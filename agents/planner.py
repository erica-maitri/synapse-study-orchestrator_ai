import json
import os
import datetime
import re
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

def safe_parse_int(val, default: int = 60) -> int:
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return int(val)
    val_str = str(val).strip()
    if not val_str:
        return default
    if val_str.isdigit():
        return int(val_str)
    
    try:
        return int(float(val_str))
    except ValueError:
        pass
        
    val_lower = val_str.lower()
    
    # Check for patterns like "1.5 hours" or "2.5 hrs"
    float_hour_match = re.search(r"(\d+\.\d+)\s*h", val_lower)
    if float_hour_match:
        return int(float(float_hour_match.group(1)) * 60)
        
    # Check for patterns like "2 hours" or "1 hour 30 mins"
    hour_match = re.search(r"(\d+)\s*h", val_lower)
    min_match = re.search(r"(\d+)\s*m", val_lower)
    
    if hour_match:
        hours = int(hour_match.group(1))
        minutes = int(min_match.group(1)) if min_match else 0
        return hours * 60 + minutes
    elif min_match:
        return int(min_match.group(1))
        
    # Fallback: extract first sequence of digits
    num_match = re.search(r"\d+", val_str)
    if num_match:
        return int(num_match.group(0))
        
    return default

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

def parse_markdown_to_dict(text: str) -> dict:
    data = {}
    
    # Try to extract key-value patterns like "- Key: Value" or "Key: Value"
    patterns = [
        r"(?:-|\*)\s*[\*\_]*([a-zA-Z\s_]+)[\*\_]*\s*:\s*(.*)",
        r"([a-zA-Z\s_]+)\s*:\s*(.*)"
    ]
    
    for line in text.splitlines():
        for pattern in patterns:
            match = re.match(pattern, line.strip())
            if match:
                key = match.group(1).strip().lower().replace(" ", "_")
                val = match.group(2).strip()
                # Clean up any trailing/leading markdown formatting
                val = val.strip("*_`\"'")
                data[key] = val
                break
                
    # Normalize keys to match scored_data
    normalized = {}
    if "title" in data: normalized["title"] = data["title"]
    if "description" in data: normalized["description"] = data["description"]
    if "importance" in data:
        try: normalized["importance"] = int(data["importance"])
        except ValueError: pass
    if "urgency" in data:
        try: normalized["urgency"] = int(data["urgency"])
        except ValueError: pass
    if "estimated_duration" in data:
        val = data["estimated_duration"]
        digits = "".join(c for c in val if c.isdigit())
        if digits: normalized["estimated_duration"] = int(digits)
    if "due_date" in data: normalized["due_date"] = data["due_date"]
    if "priority_score" in data:
        try: normalized["priority_score"] = float(data["priority_score"])
        except ValueError: pass
    elif "score" in data:
        try: normalized["priority_score"] = float(data["score"])
        except ValueError: pass
    if "quadrant" in data: normalized["quadrant"] = data["quadrant"]
    
    return normalized

planner_agent = Agent(
    name="PlannerAgent",
    model=planner_model,
    instruction=(
        "You are the Planner Agent (Root Orchestrator) of the Synapse system.\n"
        "Your task is to take the user's high-level goal and decompose it into appropriate discrete subtasks.\n\n"
        "CRITICAL RULES:\n"
        "1. MULTIPLE TASKS: If the user goal contains multiple distinct tasks, goals, or items (often separated by 'and', commas, or context shifts), you MUST create separate subtask objects for each one.\n"
        "2. CONSECUTIVE/RECURRING DAYS: If a task mentions doing something for consecutive/continuous days (e.g., 'practice DP for consecutive 5 days' or 'study ML for consecutive 3 days'), you MUST generate a separate, distinct subtask object for EACH of the consecutive days (e.g., 'DP Practice: Day 1', 'DP Practice: Day 2', ..., 'DP Practice: Day 5'). Set the `due_date` of each subsequent day's subtask to the corresponding consecutive date, starting from tomorrow.\n"
        "3. DEADLINES/DUE DATES: Pay close attention to explicit deadlines in the text (e.g., 'complete till 10 july' or 'by 15 july'). Infer the year based on the current date provided (e.g. if today is 2026-07-06, '10 july' is '2026-07-10'). Set the `due_date` of the task to that date. Do not invent dates or push tasks beyond their explicit deadline date (e.g. if the user says 'complete till 10 july', the due_date MUST be '2026-07-10' or earlier, never later).\n"
        "4. JSON FORMAT ONLY: Output ONLY a valid JSON array of objects. Do not write any conversational text, explanations, or introductory/concluding text. Only output the JSON array.\n"
        "5. DESCRIPTION INTEGRITY: Make sure descriptions match the actual subtask context. Do NOT copy the example titles or descriptions into the generated tasks.\n\n"
        "For each subtask, you must define:\n"
        "- 'title': concise task title (e.g. 'DP Practice: Day 1')\n"
        "- 'description': detailed study/review steps\n"
        "- 'importance': rating from 1 to 5 (estimate based on goal)\n"
        "- 'urgency': rating from 1 to 5 (estimate based on goal & due date)\n"
        "- 'estimated_duration': time in minutes (e.g., 30, 45, 60, 120)\n"
        "- 'due_date': YYYY-MM-DD format (infer relative to today's date if not specified)\n"
        "- 'type': either 'study' (requires creating study materials/reviews) or 'general' (just task execution)\n\n"
        "Example output:\n"
        "[\n"
        "  {\n"
        "    \"title\": \"DP Practice: Day 1\",\n"
        "    \"description\": \"Solve 10 dynamic programming questions and analyze their complexity.\",\n"
        "    \"importance\": 4,\n"
        "    \"urgency\": 4,\n"
        "    \"estimated_duration\": 120,\n"
        "    \"due_date\": \"2026-07-08\",\n"
        "    \"type\": \"study\"\n"
        "  },\n"
        "  {\n"
        "    \"title\": \"Buy groceries\",\n"
        "    \"description\": \"Purchase milk, eggs, and bread from the supermarket.\",\n"
        "    \"importance\": 2,\n"
        "    \"urgency\": 3,\n"
        "    \"estimated_duration\": 30,\n"
        "    \"due_date\": \"2026-07-07\",\n"
        "    \"type\": \"general\"\n"
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
    
    # Keep track of scheduling times per date (format: "YYYY-MM-DD")
    daily_time_slots = {}
    default_schedule_date = datetime.date.today() + datetime.timedelta(days=1)
    
    # Pre-collect study tasks for batched flashcard generation
    study_tasks = []
    for task_data in subtasks:
        is_study_task = False
        task_type = str(task_data.get("type", "")).lower().strip()
        if task_type == "study":
            is_study_task = True
        else:
            study_keywords = ["study", "practice", "read", "summarize", "learn", "review", "exam", "paper", "concept"]
            title_lower = str(task_data.get("title", "")).lower()
            desc_lower = str(task_data.get("description", "")).lower()
            if any(k in title_lower or k in desc_lower for k in study_keywords):
                is_study_task = True
        if is_study_task:
            study_tasks.append(task_data)
            
    # Batched Flashcard Generation
    flashcards_by_subject = {}
    if study_tasks:
        results["logs"].append(f"Study agent generating flashcards for {len(study_tasks)} tasks in batch.")
        study_prompt = (
            f"Generate exactly 3 high-quality flashcards for each of the following study topics:\n"
            f"{json.dumps([{'title': t.get('title'), 'description': t.get('description')} for t in study_tasks])}\n\n"
            "Quality rules:\n"
            "- Do NOT split sequential steps or list items (e.g., step 5 as question, step 6 as answer). They must form a complete Q&A pair.\n"
            "- The 'front' must be a clear, specific question, prompt, or term to define (e.g., 'What is X?' or 'Why do we need Y?').\n"
            "- The 'back' must be the direct, concise answer.\n"
            "- Do NOT prefix questions or answers with arbitrary sequential numbers (like '1.', '2.', '5.') unless they describe a count (e.g., '3 main steps').\n"
            "- Ensure the cards test active recall effectively.\n\n"
            "Format rule:\n"
            "Always respond with a JSON object containing a 'flashcards' key pointing to a list of flashcard objects. "
            "Each flashcard object in the list must be a separate dictionary containing exactly three fields: 'subject', 'front', and 'back'. "
            "Set 'subject' to the exact title of the study topic the flashcard is generated for.\n"
            "Do NOT group multiple questions/answers under duplicate keys in a single object; generate a separate object in the list for each individual flashcard (so there will be a total of 3 * number of topics separate objects in the list).\n"
            "Return ONLY valid JSON."
        )
        try:
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
                start_idx = study_raw.find("{")
                end_idx = study_raw.rfind("}")
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    study_raw_cleaned = study_raw[start_idx:end_idx+1]
                    study_raw_cleaned = re.sub(r',\s*([\]}])', r'\1', study_raw_cleaned)
                    data = json.loads(study_raw_cleaned)
                    fcs = data.get("flashcards", [])
                else:
                    raise ValueError("No JSON object found in response")
            except Exception as fc_err:
                print(f"[Study Warning] Failed to parse JSON, trying regex extractor. Error: {fc_err}")
                pattern = r'\{\s*[\'"]subject[\'"]\s*:\s*[\'"](.*?)[\'"]\s*,\s*[\'"]front[\'"]\s*:\s*[\'"](.*?)[\'"]\s*,\s*[\'"]back[\'"]\s*:\s*[\'"](.*?)[\'"]\s*\}'
                matches = re.findall(pattern, study_raw, re.DOTALL)
                if matches:
                    fcs = [{"subject": m[0].strip(), "front": m[1].strip(), "back": m[2].strip()} for m in matches]
                    print(f"[Study Info] Successfully extracted {len(fcs)} flashcards using regex fallback.")
                else:
                    raise fc_err
            
            # Group flashcards by subject
            for fc in fcs:
                subject = fc.get("subject", "General")
                if subject not in flashcards_by_subject:
                    flashcards_by_subject[subject] = []
                flashcards_by_subject[subject].append(fc)
                
        except Exception as batch_fc_err:
            print(f"[Study Warning] Batch flashcard generation failed: {batch_fc_err}. Will fallback to default cards during loop.")
            
    for task_data in subtasks:
        try:
            # Step 2: Optimize and prioritize task locally in Python (Bypass TaskOptimizer Agent)
            results["logs"].append(f"Optimizing task: {task_data.get('title', 'Untitled Task')}")
            
            imp = safe_parse_int(task_data.get("importance", 3), 3)
            urg = safe_parse_int(task_data.get("urgency", 3), 3)
            due = task_data.get("due_date")
            
            task_date = None
            if due:
                try:
                    task_date = datetime.datetime.strptime(due.strip(), "%Y-%m-%d").date()
                except ValueError:
                    pass
            
            if not task_date:
                task_date = default_schedule_date
                due = default_schedule_date.isoformat()
                
            if task_date < datetime.date.today():
                task_date = default_schedule_date
                due = default_schedule_date.isoformat()
                
            scoring = calculate_priority_score(imp, urg, due)
            
            title_val = task_data.get("title", "Untitled Task")
            if isinstance(title_val, list):
                title_val = " ".join(str(item) for item in title_val)
            else:
                title_val = str(title_val)

            desc_val = task_data.get("description", "")
            if isinstance(desc_val, list):
                desc_val = "\n".join(str(item) for item in desc_val)
            else:
                desc_val = str(desc_val)

            scored_data = {
                "title": title_val,
                "description": desc_val,
                "importance": imp,
                "urgency": urg,
                "priority_score": scoring["score"],
                "quadrant": scoring["quadrant"],
                "estimated_duration": safe_parse_int(task_data.get("estimated_duration", 60), 60),
                "due_date": due
            }
            
            log_audit("TaskOptimizer", "score_task_priority", task_data, "success")
            
            # Insert task into Database
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO tasks (title, description, importance, urgency, score, quadrant, estimated_duration, due_date)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    scored_data["title"],
                    scored_data["description"],
                    imp,
                    urg,
                    scoring["score"],
                    scoring["quadrant"],
                    scored_data["estimated_duration"],
                    due
                )
            )
            task_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            scored_data["id"] = task_id
            results["tasks_created"].append(scored_data)
            
            # Step 3: Run Exam Study Agent if the task type is 'study' (with fallback checks)
            is_study_task = False
            task_type = str(task_data.get("type", "")).lower().strip()
            if task_type == "study":
                is_study_task = True
            else:
                study_keywords = ["study", "practice", "read", "summarize", "learn", "review", "exam", "paper", "concept"]
                title_lower = str(task_data.get("title", "")).lower()
                desc_lower = str(task_data.get("description", "")).lower()
                if any(k in title_lower or k in desc_lower for k in study_keywords):
                    is_study_task = True
                    
            if is_study_task:
                task_title = scored_data["title"]
                flashcards = flashcards_by_subject.get(task_title)
                
                if not flashcards:
                    # Try soft matching if exact title match fails
                    for subj, cards in flashcards_by_subject.items():
                        if subj.lower() in task_title.lower() or task_title.lower() in subj.lower():
                            flashcards = cards
                            break
                            
                if not flashcards:
                    # Fallback to default card
                    print(f"[Study Warning] No flashcards found for '{task_title}'. Using default concept review card.")
                    flashcards = [
                        {
                            "front": f"Concept review: {task_title}",
                            "back": f"Recall details regarding: {scored_data['description']}"
                        }
                    ]
                
                log_audit("ExamStudyAgent", "generate_flashcards", {"topic": task_title}, "success")
                
                conn = get_db_connection()
                cursor = conn.cursor()
                for fc in flashcards:
                    subject = fc.get("subject", task_title)
                    front = fc.get("front", "")
                    back = fc.get("back", "")
                    
                    if isinstance(subject, list):
                        subject = " ".join(str(item) for item in subject)
                    else:
                        subject = str(subject)
                        
                    if isinstance(front, list):
                        front = "\n".join(str(item) for item in front)
                    else:
                        front = str(front)
                        
                    if isinstance(back, list):
                        back = "\n".join(str(item) for item in back)
                    else:
                        back = str(back)
                        
                    cursor.execute(
                        "INSERT INTO flashcards (front, back, subject, next_review_date) VALUES (?, ?, ?, ?)",
                        (front, back, subject, datetime.date.today().isoformat())
                    )
                    results["flashcards_created"].append({
                        "front": front,
                        "back": back
                    })
                conn.commit()
                conn.close()
            
            # Step 4: Run Live Scheduler Agent to schedule calendar block
            date_str = task_date.isoformat()
            if date_str not in daily_time_slots:
                daily_time_slots[date_str] = datetime.datetime.combine(task_date, datetime.time(10, 0))
                
            current_time_slot = daily_time_slots[date_str]
            
            duration_mins = scored_data["estimated_duration"]
            end_time_slot = current_time_slot + datetime.timedelta(minutes=duration_mins)
            
            start_str = current_time_slot.isoformat()
            end_str = end_time_slot.isoformat()
            
            results["logs"].append(f"Scheduling calendar event for: {scored_data['title']} on {date_str}")
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO calendar_events (title, description, start_time, end_time, task_id) VALUES (?, ?, ?, ?, ?)",
                (scored_data["title"], scored_data["description"], start_str, end_str, task_id)
            )
            event_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
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
            
            # Advance schedule time slot for next task on this date (add a 15 min break)
            daily_time_slots[date_str] = end_time_slot + datetime.timedelta(minutes=15)
            
        except Exception as task_err:
            print(f"[Pipeline Error on Task] {task_err}")
            log_audit("PlannerAgent", "ProcessSubtask", task_data, "error", str(task_err))
            results["logs"].append(f"Error processing task '{task_data.get('title')}': {task_err}")
            
    results["logs"].append("Pipeline execution completed successfully.")
    return results
