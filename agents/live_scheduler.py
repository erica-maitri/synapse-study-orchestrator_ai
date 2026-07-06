import json
import sqlite3
from google.adk.agents import Agent
from agents.base import subagent_model
from mcp_server.database import get_db_connection

def list_calendar_events() -> str:
    """
    Retrieves all scheduled calendar events from the local database.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, description, start_time, end_time, task_id, is_completed FROM calendar_events ORDER BY start_time ASC")
        rows = cursor.fetchall()
        events = [dict(row) for row in rows]
        conn.close()
        return json.dumps(events)
    except Exception as e:
        return json.dumps({"error": str(e)})

def schedule_event(title: str, start_time: str, end_time: str, description: str = None, task_id: int = None) -> str:
    """
    Creates a new calendar event in the database.
    
    Parameters:
      title (str): Event title
      start_time (str): ISO start timestamp (YYYY-MM-DDTHH:MM:SS)
      end_time (str): ISO end timestamp (YYYY-MM-DDTHH:MM:SS)
      description (str): Event description (optional)
      task_id (int): Associated task ID (optional)
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO calendar_events (title, description, start_time, end_time, task_id) VALUES (?, ?, ?, ?, ?)",
            (title, description, start_time, end_time, task_id)
        )
        conn.commit()
        event_id = cursor.lastrowid
        conn.close()
        return json.dumps({"status": "success", "event_id": event_id})
    except Exception as e:
        return json.dumps({"error": str(e)})

def reschedule_event(event_id: int, new_start_time: str, new_end_time: str) -> str:
    """
    Reschedules an existing calendar event.
    
    Parameters:
      event_id (int): The ID of the event to reschedule
      new_start_time (str): New ISO start timestamp
      new_end_time (str): New ISO end timestamp
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE calendar_events SET start_time = ?, end_time = ? WHERE id = ?",
            (new_start_time, new_end_time, event_id)
        )
        conn.commit()
        conn.close()
        return json.dumps({"status": "success", "message": "Event rescheduled"})
    except Exception as e:
        return json.dumps({"error": str(e)})

live_scheduler_agent = Agent(
    name="LiveSchedulerAgent",
    model=subagent_model,
    instruction=(
        "You are the Live Scheduler Agent. Your job is to manage the calendar and timetable events.\n\n"
        "Capabilities:\n"
        "1. List calendar events using the 'list_calendar_events' tool.\n"
        "2. Schedule new study sessions using the 'schedule_event' tool.\n"
        "3. Handle rescheduling and conflict resolution when tasks slip or overlap using the 'reschedule_event' tool.\n\n"
        "Always reconcile calendar changes with task priority. Focus scheduled blocks on higher priority tasks first."
    ),
    tools=[list_calendar_events, schedule_event, reschedule_event]
)
