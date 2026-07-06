import os
import json
import datetime
import time
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import pypdf
import io
from fastapi.responses import Response, StreamingResponse
from pydantic import ValidationError
from dotenv import load_dotenv

from mcp_server.database import get_db_connection, init_db
from mcp_server.auth import (
    verify_password,
    create_access_token,
    get_current_user,
    get_password_hash,
    JWT_SECRET,
    JWT_ALGORITHM
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

security_optional = HTTPBearer(auto_error=False)
from mcp_server.schemas import (
    UserLogin,
    TaskCreate,
    TaskUpdate,
    CalendarEventCreate,
    FlashcardCreate,
    FlashcardUpdate,
    FlashcardReview,
    SandboxFileOperation
)
from skills.task_scoring.score import calculate_priority_score
from skills.spaced_repetition.sm2 import calculate_next_review
from agents.planner import run_synapse_pipeline

load_dotenv()

# Initialize DB on startup
init_db()

app = FastAPI(title="Synapse Core API & MCP Server")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the actual frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




# --- SECURITY SANDBOX SANITIZATION HELPER ---
SANDBOX_ROOT = os.path.abspath(os.getenv("SANDBOX_DIR", "mcp_server/sandbox"))
if not os.path.exists(SANDBOX_ROOT):
    os.makedirs(SANDBOX_ROOT)

def secure_sandbox_path(user_path: str) -> str:
    # Resolve absolute target path
    abs_target = os.path.abspath(os.path.join(SANDBOX_ROOT, user_path))
    # Safety Check: Target path must begin with sandbox root directory path
    if not abs_target.startswith(SANDBOX_ROOT):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Access denied outside sandbox context."
        )
    return abs_target


# --- AUTHENTICATION ---
@app.post("/api/auth/login")
def login(login_data: UserLogin):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE username = ?", (login_data.username,))
    row = cursor.fetchone()
    conn.close()
    
    if not row or not verify_password(login_data.password, row["password_hash"]):
        raise HTTPException(status_code=400, detail="Invalid username or password")
        
    token = create_access_token(data={"sub": login_data.username})
    return {"access_token": token, "token_type": "bearer"}

@app.post("/api/auth/register")
def register(login_data: UserLogin):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if user already exists
    cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", (login_data.username,))
    if cursor.fetchone()[0] > 0:
        conn.close()
        raise HTTPException(status_code=400, detail="Username already exists")
        
    try:
        hashed = get_password_hash(login_data.password)
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (login_data.username, hashed))
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Registration failed: {e}")
        
    conn.close()
    return {"status": "success", "message": "User registered successfully"}


# --- TASK MANAGER ---
@app.get("/api/tasks")
def list_tasks(current_user: str = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks ORDER BY score DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.post("/api/tasks")
def create_task(task: TaskCreate, current_user: str = Depends(get_current_user)):
    # Calculate score & quadrant using inspectable scoring logic
    scoring = calculate_priority_score(task.importance, task.urgency, task.due_date)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO tasks (title, description, importance, urgency, score, quadrant, estimated_duration, due_date)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (task.title, task.description, task.importance, task.urgency, scoring["score"], scoring["quadrant"], task.estimated_duration, task.due_date)
    )
    conn.commit()
    task_id = cursor.lastrowid
    conn.close()
    
    return {"id": task_id, "status": "success", "score": scoring["score"], "quadrant": scoring["quadrant"]}

@app.put("/api/tasks/{task_id}")
def update_task(task_id: int, task: TaskUpdate, current_user: str = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Load original task
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    orig = cursor.fetchone()
    if not orig:
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found")
        
    # Re-score task if priority criteria change
    importance = task.importance if task.importance is not None else orig["importance"]
    urgency = task.urgency if task.urgency is not None else orig["urgency"]
    due_date = task.due_date if task.due_date is not None else orig["due_date"]
    
    scoring = calculate_priority_score(importance, urgency, due_date)
    
    fields = {
        "status": task.status if task.status is not None else orig["status"],
        "title": task.title if task.title is not None else orig["title"],
        "description": task.description if task.description is not None else orig["description"],
        "importance": importance,
        "urgency": urgency,
        "score": scoring["score"],
        "quadrant": scoring["quadrant"],
        "estimated_duration": task.estimated_duration if task.estimated_duration is not None else orig["estimated_duration"],
        "due_date": due_date
    }
    
    query = ", ".join([f"{k} = ?" for k in fields.keys()])
    params = list(fields.values()) + [task_id]
    
    cursor.execute(f"UPDATE tasks SET {query} WHERE id = ?", params)
    conn.commit()
    conn.close()
    
    return {"id": task_id, "status": "success", "score": scoring["score"], "quadrant": scoring["quadrant"]}

@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: int, current_user: str = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Delete associated calendar events first to maintain database integrity
    cursor.execute("DELETE FROM calendar_events WHERE task_id = ?", (task_id,))
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}


# --- CALENDAR TIMETABLE ---
def resolve_calendar_overlaps():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Query all events sorted by start_time ASC
    cursor.execute("SELECT id, title, start_time, end_time FROM calendar_events ORDER BY start_time ASC")
    events = [dict(row) for row in cursor.fetchall()]
    
    if not events:
        conn.close()
        return
        
    updated = False
    for i in range(1, len(events)):
        prev_event = events[i - 1]
        curr_event = events[i]
        
        try:
            prev_end = datetime.datetime.fromisoformat(prev_event["end_time"])
            curr_start = datetime.datetime.fromisoformat(curr_event["start_time"])
            curr_end = datetime.datetime.fromisoformat(curr_event["end_time"])
        except ValueError:
            continue
            
        if curr_start < prev_end:
            # Overlap detected! Shift current event start time to previous event's end time
            duration = curr_end - curr_start
            new_start = prev_end
            new_end = new_start + duration
            
            new_start_str = new_start.isoformat()
            new_end_str = new_end.isoformat()
            
            cursor.execute(
                "UPDATE calendar_events SET start_time = ?, end_time = ? WHERE id = ?",
                (new_start_str, new_end_str, curr_event["id"])
            )
            
            # Update our local copy so the next iteration uses the updated end time
            events[i]["start_time"] = new_start_str
            events[i]["end_time"] = new_end_str
            updated = True
            print(f"[CONFLICT RESOLVER] Shifted event '{curr_event['title']}' to {new_start_str} - {new_end_str} to resolve overlap with '{prev_event['title']}'")
            
    if updated:
        conn.commit()
    conn.close()

@app.get("/api/calendar")
def list_calendar(current_user: str = Depends(get_current_user)):
    resolve_calendar_overlaps()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM calendar_events ORDER BY start_time ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.post("/api/calendar")
def create_calendar_event(event: CalendarEventCreate, current_user: str = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO calendar_events (title, description, start_time, end_time, task_id) VALUES (?, ?, ?, ?, ?)",
        (event.title, event.description, event.start_time, event.end_time, event.task_id)
    )
    conn.commit()
    event_id = cursor.lastrowid
    conn.close()
    resolve_calendar_overlaps()
    return {"id": event_id, "status": "success"}

@app.delete("/api/calendar/{event_id}")
def delete_calendar_event(event_id: int, current_user: str = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM calendar_events WHERE id = ?", (event_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}

# Timetable iCal Export (.ics)
@app.get("/api/calendar/export")
def export_calendar_ics(
    token: Optional[str] = None,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional)
):
    # Try getting token from authorization header first, then fallback to URL query parameter
    actual_token = None
    if credentials:
        actual_token = credentials.credentials
    elif token:
        actual_token = token
        
    if not actual_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
        
    try:
        payload = jwt.decode(actual_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM calendar_events WHERE is_completed = 0")
    events = cursor.fetchall()
    conn.close()
    
    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Synapse//Study Scheduler//EN",
        "CALSCALE:GREGORIAN"
    ]
    
    for event in events:
        # Format dates for .ics: YYYYMMDDTHHMMSS
        # Strips dash/colon separators from ISO formats
        try:
            start_dt = datetime.datetime.fromisoformat(event["start_time"]).strftime("%Y%m%dT%H%M%S")
            end_dt = datetime.datetime.fromisoformat(event["end_time"]).strftime("%Y%m%dT%H%M%S")
        except Exception:
            # Fallback
            start_dt = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
            end_dt = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
            
        desc = event["description"] or ""
        
        ics_lines.extend([
            "BEGIN:VEVENT",
            f"SUMMARY:{event['title']}",
            f"DESCRIPTION:{desc}",
            f"DTSTART:{start_dt}",
            f"DTEND:{end_dt}",
            f"UID:event_{event['id']}@synapse.local",
            "END:VEVENT"
        ])
        
    ics_lines.append("END:VCALENDAR")
    ics_content = "\r\n".join(ics_lines)
    
    return Response(
        content=ics_content,
        media_type="text/calendar",
        headers={"Content-Disposition": "attachment; filename=study_schedule.ics"}
    )


# --- SPACED REPETITION FLASHCARDS ---
@app.get("/api/flashcards")
def list_flashcards(current_user: str = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    # List flashcards due on or before today
    today_str = datetime.date.today().isoformat()
    cursor.execute("SELECT * FROM flashcards WHERE next_review_date <= ? ORDER BY next_review_date ASC", (today_str,))
    rows = cursor.fetchall()
    
    # If no card is due, return all cards for statistics
    if not rows:
        cursor.execute("SELECT * FROM flashcards")
        rows = cursor.fetchall()
        
    conn.close()
    return [dict(row) for row in rows]

@app.post("/api/flashcards")
def create_flashcard(fc: FlashcardCreate, current_user: str = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        reps = fc.repetitions if fc.repetitions is not None else 0
        ef = fc.ease_factor if fc.ease_factor is not None else 2.5
        interval = fc.interval_days if fc.interval_days is not None else 0
        
        cursor.execute(
            """INSERT INTO flashcards (front, back, subject, image, repetitions, ease_factor, interval_days, next_review_date) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (fc.front, fc.back, fc.subject or "General", fc.image, reps, ef, interval, datetime.date.today().isoformat())
        )
        conn.commit()
        fc_id = cursor.lastrowid
        conn.close()
        print(f"[DB LOG] Flashcard created: ID={fc_id}, Subject='{fc.subject}', Reps={reps}, EF={ef}, Interval={interval}, Image={fc.image is not None}")
        return {"id": fc_id, "status": "success"}
    except Exception as e:
        if conn:
            conn.close()
        print(f"[DB ERROR] Failed to create flashcard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/flashcards/{fc_id}")
def update_flashcard(fc_id: int, fc: FlashcardUpdate, current_user: str = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM flashcards WHERE id = ?", (fc_id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Flashcard not found")
        
    updates = {}
    if fc.front is not None:
        updates["front"] = fc.front
    if fc.back is not None:
        updates["back"] = fc.back
    if fc.subject is not None:
        updates["subject"] = fc.subject or "General"
    if fc.image is not None:
        updates["image"] = fc.image
        
    if updates:
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        params = list(updates.values()) + [fc_id]
        cursor.execute(f"UPDATE flashcards SET {set_clause} WHERE id = ?", params)
        conn.commit()
        
    conn.close()
    return {"status": "success"}

@app.delete("/api/flashcards/{fc_id}")
def delete_flashcard(fc_id: int, current_user: str = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM flashcards WHERE id = ?", (fc_id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Flashcard not found")
        
    cursor.execute("DELETE FROM flashcards WHERE id = ?", (fc_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/api/flashcards/{fc_id}/review")
def review_flashcard(fc_id: int, review: FlashcardReview, current_user: str = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM flashcards WHERE id = ?", (fc_id,))
    fc = cursor.fetchone()
    
    if not fc:
        conn.close()
        raise HTTPException(status_code=404, detail="Flashcard not found")
        
    # Calculate next scheduled intervals using SM-2
    scheduled = calculate_next_review(
        quality=review.quality,
        repetitions=fc["repetitions"],
        ease_factor=fc["ease_factor"],
        interval=fc["interval_days"]
    )
    
    cursor.execute(
        """UPDATE flashcards 
           SET repetitions = ?, interval_days = ?, ease_factor = ?, next_review_date = ?
           WHERE id = ?""",
        (
            scheduled["next_repetitions"],
            scheduled["next_interval"],
            scheduled["next_ease_factor"],
            scheduled["next_review_date"],
            fc_id
        )
    )
    
    # Update streak info in review_streaks
    today_str = datetime.date.today().isoformat()
    yesterday_str = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    
    cursor.execute("SELECT * FROM review_streaks WHERE date = ?", (today_str,))
    today_record = cursor.fetchone()
    
    is_correct = 1 if review.quality >= 3 else 0
    
    if today_record:
        new_reviewed = today_record["cards_reviewed"] + 1
        new_correct = today_record["cards_correct"] + is_correct
        cursor.execute(
            "UPDATE review_streaks SET cards_reviewed = ?, cards_correct = ? WHERE date = ?",
            (new_reviewed, new_correct, today_str)
        )
    else:
        cursor.execute("SELECT streak_count FROM review_streaks WHERE date = ?", (yesterday_str,))
        yesterday_record = cursor.fetchone()
        
        if yesterday_record:
            new_streak = yesterday_record["streak_count"] + 1
        else:
            new_streak = 1
            
        cursor.execute(
            "INSERT INTO review_streaks (date, cards_reviewed, cards_correct, streak_count) VALUES (?, ?, ?, ?)",
            (today_str, 1, is_correct, new_streak)
        )
        
    conn.commit()
    conn.close()
    
    return {
        "id": fc_id,
        "status": "success",
        "next_repetitions": scheduled["next_repetitions"],
        "next_interval": scheduled["next_interval"],
        "next_ease_factor": scheduled["next_ease_factor"],
        "next_review_date": scheduled["next_review_date"]
    }

@app.get("/api/vault/streak")
def get_streak(current_user: str = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM review_streaks ORDER BY date DESC LIMIT 1")
    latest = cursor.fetchone()
    conn.close()
    
    if not latest:
        return {"current_streak": 0, "last_reviewed_date": None}
        
    today = datetime.date.today()
    last_date = datetime.date.fromisoformat(latest["date"])
    delta_days = (today - last_date).days
    
    if delta_days == 0:
        current_streak = latest["streak_count"]
    elif delta_days == 1:
        current_streak = latest["streak_count"]
    else:
        current_streak = 0
        
    return {"current_streak": current_streak, "last_reviewed_date": latest["date"]}

@app.get("/api/vault/history")
def get_vault_history(days: int = 30, current_user: str = Depends(get_current_user)):
    start_date = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM review_streaks WHERE date >= ? ORDER BY date ASC", (start_date,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/api/vault/due")
def get_due_flashcards(all: bool = False, date: Optional[str] = None, current_user: str = Depends(get_current_user)):
    if date:
        try:
            today_date = datetime.date.fromisoformat(date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        today_date = datetime.date.today()
        
    today_str = today_date.isoformat()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if all:
        # Fetch every flashcard, ordered by id DESC
        cursor.execute("SELECT * FROM flashcards ORDER BY id DESC")
    else:
        # Query due cards, sorted by next_review_date ASC (oldest due date first)
        cursor.execute(
            "SELECT * FROM flashcards WHERE next_review_date <= ? ORDER BY next_review_date ASC",
            (today_str,)
        )
    rows = cursor.fetchall()
    conn.close()
    
    due_cards = []
    for row in rows:
        next_review_str = row["next_review_date"]
        try:
            next_review = datetime.date.fromisoformat(next_review_str)
            days_overdue = (today_date - next_review).days
        except Exception:
            days_overdue = 0
            
        due_cards.append({
            "card_id": row["id"],
            "id": row["id"],  # Keep "id" for compatibility with Flashcards.jsx
            "front": row["front"],
            "back": row["back"],
            "subject": row["subject"] if row["subject"] else "General",
            "tag": row["subject"] if row["subject"] else "General", # subject/tag
            "image": row["image"],
            "days_overdue": days_overdue,
            "streak": row["repetitions"],  # current streak count
            "repetitions": row["repetitions"],
            "ease_factor": row["ease_factor"],
            "next_review_date": row["next_review_date"]
        })
        
    return due_cards


# --- AGENT RUN ORCHESTRATOR ---
@app.post("/api/agent/run")
def run_agent_pipeline(request: Request, current_user: str = Depends(get_current_user)):
    # Parse query JSON body
    import asyncio
    try:
        body = json.loads(request.state.body if hasattr(request.state, "body") else b"{}")
    except Exception:
        body = {}
        
    # Standard route reading of request JSON
    async def get_body(req: Request):
        return await req.json()
        
    # Since endpoint is normal FastAPI, let's just fetch goal parameter
    pass

@app.post("/api/agent/run-goal")
async def run_goal(data: dict, current_user: str = Depends(get_current_user)):
    goal = data.get("goal")
    if not goal:
        raise HTTPException(status_code=400, detail="Missing parameter 'goal'")
        
    # Execute the multi-agent orchestration pipeline
    pipeline_result = run_synapse_pipeline(goal)
    return pipeline_result

@app.post("/api/agent/upload-file")
async def upload_file_pipeline(
    file: UploadFile = File(...),
    current_user: str = Depends(get_current_user)
):
    filename = file.filename
    content = await file.read()
    
    extracted_text = ""
    
    if filename.lower().endswith(".pdf"):
        try:
            pdf_file = io.BytesIO(content)
            reader = pypdf.PdfReader(pdf_file)
            text_parts = []
            max_pages = min(len(reader.pages), 20)
            for i in range(max_pages):
                page_text = reader.pages[i].extract_text()
                if page_text:
                    text_parts.append(page_text)
            extracted_text = "\n".join(text_parts).strip()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse PDF file: {e}")
    else:
        try:
            extracted_text = content.decode("utf-8").strip()
        except Exception:
            try:
                extracted_text = content.decode("latin-1").strip()
            except Exception:
                raise HTTPException(status_code=400, detail="Failed to decode text file. Ensure it is UTF-8 or Latin-1 encoded.")

    if not extracted_text:
        raise HTTPException(status_code=400, detail="The uploaded file contains no readable text.")
        
    # Truncate to safe limit (8000 characters)
    max_length = 8000
    if len(extracted_text) > max_length:
        extracted_text = extracted_text[:max_length] + "\n... [TRUNCATED DUE TO LENGTH] ..."
        
    try:
        pipeline_result = run_synapse_pipeline(extracted_text)
        return {
            "status": "success",
            "filename": filename,
            "extracted_length": len(extracted_text),
            "pipeline_result": pipeline_result
        }
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {err}")


# --- AUDIT LOGS FOR INTEGRITY DEMO ---
@app.get("/api/audit-logs")
def list_audit_logs(current_user: str = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 100")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# --- SECURITY SANDBOXED FILESYSTEM ACTIONS ---
@app.post("/api/sandbox/write")
def write_sandbox_file(op: SandboxFileOperation, current_user: str = Depends(get_current_user)):
    if op.content is None:
        raise HTTPException(status_code=400, detail="Missing 'content' body")
        
    # Get secured path inside sandbox root
    target_path = secure_sandbox_path(op.file_path)
    
    try:
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(op.content)
        return {"status": "success", "file": op.file_path, "size_bytes": len(op.content)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File Write Failed: {e}")

@app.post("/api/sandbox/read")
def read_sandbox_file(op: SandboxFileOperation, current_user: str = Depends(get_current_user)):
    # Get secured path inside sandbox root
    target_path = secure_sandbox_path(op.file_path)
    
    if not os.path.exists(target_path):
        raise HTTPException(status_code=404, detail=f"File not found: {op.file_path}")
        
    try:
        with open(target_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"status": "success", "file": op.file_path, "content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File Read Failed: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("mcp_server.main:app", host="127.0.0.1", port=8000, reload=True)
