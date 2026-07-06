import json
import os
import datetime
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from agents.base import planner_model
from agents.task_optimizer import task_optimizer_agent
from agents.exam_study import exam_study_agent
from agents.live_scheduler import live_scheduler_agent
from mcp_server.database import get_db_connection
from skills.task_scoring.score import calculate_priority_score

def run_agent(agent, prompt: str) -> str:
    session_service = InMemorySessionService()
    runner = Runner(agent=agent, session_service=session_service, auto_create_session=True, app_name=agent.name)
    events = list(runner.run(
        user_id="default_user",
        session_id="session_1",
        new_message=types.Content(role="user", parts=[types.Part(text=prompt)])
    ))
    text_parts = []
    for event in events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    text_parts.append(part.text)
    return "".join(text_parts).strip()

planner_agent = Agent(
    name="PlannerAgent",
    model=planner_model,
    instruction=(
        "You are the Planner Agent (Root Orchestrator) of the Synapse system.\n"
        "Your task is to take the user's high-level goal (e.g., 'Prepare for my history exam next Monday') "
        "and decompose it into 2 to 4 discrete subtasks.\n\n"
        "For each subtask, you must define:\n"
        "- 'title': concise task title\n"
        "- 'description': detailed study/review steps\n"
        "- 'importance': rating from 1 to 5 (estimate based on goal)\n"
        "- 'urgency': rating from 1 to 5 (estimate based on goal & due date)\n"
        "- 'estimated_duration': time in minutes (e.g., 30, 45, 60, 120)\n"
        "- 'due_date': YYYY-MM-DD format (infer relative to today's date if not specified)\n"
        "- 'type': either 'study' (requires creating study materials/reviews) or 'general' (just task execution)\n\n"
        "Return the subtasks ONLY as a valid JSON array of objects. Do not include markdown code block formatting in your output, just raw JSON.\n"
        "Example output:\n"
        "[\n"
        "  {\n"
        "    \"title\": \"Read Chapter 1\",\n"
        "    \"description\": \"Review Chapter 1 notes on World War I\",\n"
        "    \"importance\": 4,\n"
        "    \"urgency\": 4,\n"
        "    \"estimated_duration\": 60,\n"
        "    \"due_date\": \"2026-07-09\",\n"
        "    \"type\": \"study\"\n"
        "  }\n"
        "]"
    )
)

def log_audit(agent_name: str, tool_name: str, params: dict, status: str, error: str = None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO audit_logs (agent_name, tool_name, parameters, status, error, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (agent_name, tool_name, json.dumps(params), status, error, datetime.datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Audit Log Error] {e}")

def run_synapse_pipeline(user_goal: str) -> dict:
    results = {
        "status": "success",
        "tasks_created": [],
        "calendar_events_created": [],
        "flashcards_created": [],
        "logs": []
    }
    
    # Step 1: Run Planner Agent to decompose goal
    log_msg = f"Planner Agent received goal: '{user_goal}'"
    results["logs"].append(log_msg)
    print(f"[Pipeline] {log_msg}")
    
    planner_response = run_agent(planner_agent, f"Decompose this goal: '{user_goal}'. Today is {datetime.date.today().isoformat()}.")
    
    # Strip any markdown backticks if returned
    raw_response = planner_response.strip()
    if raw_response.startswith("```"):
        # Strip block headers and footers
        lines = raw_response.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines[-1].startswith("```"):
            lines = lines[:-1]
        raw_response = "\n".join(lines).strip()
        
    try:
        # Try to find JSON array in the text (sometimes the model puts text around it)
        start_idx = raw_response.find("[")
        end_idx = raw_response.rfind("]")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            raw_response = raw_response[start_idx:end_idx+1]
        subtasks = json.loads(raw_response)
        if not isinstance(subtasks, list):
            raise ValueError("Parsed JSON is not a list")
    except Exception as e:
        # Fallback: create a default set of subtasks based on the user's goal
        print(f"[Planner Warning] Failed to parse JSON, using fallback. Error: {e}")
        subtasks = [
            {
                "title": f"Study and Review: {user_goal}",
                "description": f"Focus on understanding the core concepts of: {user_goal}",
                "importance": 4,
                "urgency": 4,
                "estimated_duration": 60,
                "due_date": (datetime.date.today() + datetime.timedelta(days=1)).isoformat(),
                "type": "study"
            }
        ]
        
    log_audit("PlannerAgent", "DecomposeGoal", {"goal": user_goal}, "success")
    results["logs"].append(f"Planner prepared {len(subtasks)} tasks.")
    
    # Connect to SQLite for database operations
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Schedule timeline base (start scheduling from tomorrow at 10:00 AM)
    schedule_date = datetime.date.today() + datetime.timedelta(days=1)
    current_time_slot = datetime.datetime.combine(schedule_date, datetime.time(10, 0))
    
    for task_data in subtasks:
        try:
            # Step 2: Run Task Optimizer Agent to prioritize the task
            results["logs"].append(f"Optimizing task: {task_data.get('title', 'Untitled Task')}")
            optimizer_prompt = f"Optimize and score this task: {json.dumps(task_data)}"
            opt_response = run_agent(task_optimizer_agent, optimizer_prompt)
            
            # Extract JSON from optimizer response
            opt_raw = opt_response.strip()
            if opt_raw.startswith("```"):
                lines = opt_raw.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                opt_raw = "\n".join(lines).strip()
            
            try:
                start_idx = opt_raw.find("{")
                end_idx = opt_raw.rfind("}")
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    opt_raw = opt_raw[start_idx:end_idx+1]
                scored_data = json.loads(opt_raw)
            except Exception as opt_err:
                print(f"[Optimizer Warning] Failed to parse JSON, using fallback. Error: {opt_err}")
                scored_data = {
                    "title": task_data.get("title", "Untitled Task"),
                    "description": task_data.get("description", ""),
                    "importance": task_data.get("importance", 3),
                    "urgency": task_data.get("urgency", 3),
                    "priority_score": 3.5,
                    "quadrant": "Q2: Schedule",
                    "estimated_duration": task_data.get("estimated_duration", 60),
                    "due_date": task_data.get("due_date", (datetime.date.today() + datetime.timedelta(days=1)).isoformat())
                }
                
            log_audit("TaskOptimizer", "score_task_priority", task_data, "success")
            
            # Calculate score & quadrant deterministically in Python to prevent LLM mismatches
            imp = int(scored_data.get("importance", task_data.get("importance", 3)))
            urg = int(scored_data.get("urgency", task_data.get("urgency", 3)))
            due = scored_data.get("due_date", task_data.get("due_date", (datetime.date.today() + datetime.timedelta(days=1)).isoformat()))
            scoring = calculate_priority_score(imp, urg, due)

            # Insert task into Database
            cursor.execute(
                """INSERT INTO tasks (title, description, importance, urgency, score, quadrant, estimated_duration, due_date)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    scored_data.get("title", task_data.get("title", "Untitled Task")),
                    scored_data.get("description", task_data.get("description", "")),
                    imp,
                    urg,
                    scoring["score"],
                    scoring["quadrant"],
                    int(scored_data.get("estimated_duration", task_data.get("estimated_duration", 60))),
                    due
                )
            )
            task_id = cursor.lastrowid
            scored_data["id"] = task_id
            results["tasks_created"].append(scored_data)
            
            # Step 3: Run Exam Study Agent if the task type is 'study'
            if task_data.get("type") == "study":
                results["logs"].append(f"Study agent generating flashcards for: {task_data.get('title', 'Untitled Task')}")
                study_prompt = (
                    f"Generate 3 high-quality flashcards for study topic: '{task_data.get('title', 'Untitled Task')}' with context '{task_data.get('description', '')}'. "
                    "Rule: The 'front' must be a clear, active-recall question or term (e.g., 'What is X?' or 'Why do we need Y?'). "
                    "The 'back' must be the direct answer. Do NOT split adjacent steps or list items across front/back, "
                    "and do not prefix with numbered list indices. Return ONLY a JSON list of objects containing 'front' and 'back'."
                )
                study_response = run_agent(exam_study_agent, study_prompt)
                
                study_raw = study_response.strip()
                if study_raw.startswith("```"):
                    lines = study_raw.splitlines()
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines[-1].startswith("```"):
                        lines = lines[:-1]
                    study_raw = "\n".join(lines).strip()
                
                try:
                    start_idx = study_raw.find("[")
                    end_idx = study_raw.rfind("]")
                    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                        study_raw = study_raw[start_idx:end_idx+1]
                    flashcards = json.loads(study_raw)
                except Exception as fc_err:
                    print(f"[Study Warning] Failed to parse JSON, using fallback. Error: {fc_err}")
                    flashcards = [
                        {
                            "front": f"Concept review: {task_data.get('title', 'Untitled Task')}",
                            "back": f"Recall details regarding: {task_data.get('description', '')}"
                        }
                    ]
                    
                log_audit("ExamStudyAgent", "generate_flashcards", {"topic": task_data.get('title', 'Untitled Task')}, "success")
                
                for fc in flashcards:
                    subject = fc.get("subject", fc.get("tag", task_data.get('title', 'Untitled Task')))
                    cursor.execute(
                        "INSERT INTO flashcards (front, back, subject, next_review_date) VALUES (?, ?, ?, ?)",
                        (fc["front"], fc["back"], subject, datetime.date.today().isoformat())
                    )
                    results["flashcards_created"].append({
                        "front": fc["front"],
                        "back": fc["back"]
                    })
            
            # Step 4: Run Live Scheduler Agent to schedule calendar block
            duration_mins = int(scored_data.get("estimated_duration", 60))
            end_time_slot = current_time_slot + datetime.timedelta(minutes=duration_mins)
            
            start_str = current_time_slot.isoformat()
            end_str = end_time_slot.isoformat()
            
            results["logs"].append(f"Scheduling calendar event for: {task_data.get('title', 'Untitled Task')}")
            
            # Schedule calendar event via tool invocation inside scheduler agent or direct insertion
            cursor.execute(
                "INSERT INTO calendar_events (title, description, start_time, end_time, task_id) VALUES (?, ?, ?, ?, ?)",
                (scored_data["title"], scored_data["description"], start_str, end_str, task_id)
            )
            event_id = cursor.lastrowid
            
            log_audit("LiveSchedulerAgent", "schedule_event", {
                "title": scored_data["title"],
                "start_time": start_str,
                "end_time": end_str
            }, "success")
            
            results["calendar_events_created"].append({
                "id": event_id,
                "title": scored_data["title"],
                "start_time": start_str,
                "end_time": end_str,
                "task_id": task_id
            })
            
            # Advance schedule time slot for next task (add a 15 min break)
            current_time_slot = end_time_slot + datetime.timedelta(minutes=15)
            
        except Exception as task_err:
            print(f"[Pipeline Error on Task] {task_err}")
            log_audit("PlannerAgent", "ProcessSubtask", task_data, "error", str(task_err))
            results["logs"].append(f"Error processing task '{task_data.get('title')}': {task_err}")
            
    conn.commit()
    conn.close()
    
    results["logs"].append("Pipeline execution completed successfully.")
    return results
