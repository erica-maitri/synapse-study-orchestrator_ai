import json
from google.adk.agents import Agent
from agents.base import subagent_model
from skills.task_scoring.score import calculate_priority_score

# Define the tool wrapper for the agent
def score_task_priority(importance: int, urgency: int, due_date: str = None) -> str:
    """
    Computes priority score and Eisenhower quadrant based on importance, urgency, and optional due date.
    
    Parameters:
      importance (int): Importance rating from 1 (lowest) to 5 (highest).
      urgency (int): Urgency rating from 1 (lowest) to 5 (highest).
      due_date (str): Optional due date in YYYY-MM-DD format.
    """
    result = calculate_priority_score(importance, urgency, due_date)
    return json.dumps(result)

task_optimizer_agent = Agent(
    name="TaskOptimizer",
    model=subagent_model,
    instruction=(
        "You are the Task Optimization Agent. Your job is to extract task metadata "
        "from task descriptions and run the 'score_task_priority' tool to compute their priority score.\n\n"
        "Steps:\n"
        "1. Identify the task's title, description, and estimated duration (default to 30 mins if not specified).\n"
        "2. Rate the task's importance (1-5) and urgency (1-5) based on the user's description.\n"
        "3. Identify the due date in YYYY-MM-DD format (if provided).\n"
        "4. Call the 'score_task_priority' tool with importance, urgency, and due_date.\n"
        "5. Output a final JSON object with the following fields: 'title', 'description', 'importance', "
        "'urgency', 'estimated_duration', 'due_date', 'priority_score', 'quadrant'.\n\n"
        "Example output:\n"
        "{\n"
        "  \"title\": \"Read History Chapter 3\",\n"
        "  \"description\": \"Read Chapter 3 on French Revolution\",\n"
        "  \"importance\": 3,\n"
        "  \"urgency\": 2,\n"
        "  \"estimated_duration\": 45,\n"
        "  \"due_date\": \"2026-07-12\",\n"
        "  \"priority_score\": 2.8,\n"
        "  \"quadrant\": \"Q2: Schedule\"\n"
        "}"
    ),
    tools=[score_task_priority]
)
