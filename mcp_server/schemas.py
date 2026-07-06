from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
import datetime

class UserLogin(BaseModel):
    username: str
    password: str

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    importance: int = Field(..., ge=1, le=5)
    urgency: int = Field(..., ge=1, le=5)
    estimated_duration: Optional[int] = Field(30, ge=5, le=480)
    due_date: Optional[str] = None

    @field_validator("due_date")
    @classmethod
    def validate_due_date(cls, v):
        if v:
            try:
                datetime.date.fromisoformat(v)
            except ValueError:
                raise ValueError("due_date must be in YYYY-MM-DD format")
        return v

class TaskUpdate(BaseModel):
    status: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    importance: Optional[int] = Field(None, ge=1, le=5)
    urgency: Optional[int] = Field(None, ge=1, le=5)
    score: Optional[float] = None
    quadrant: Optional[str] = None
    estimated_duration: Optional[int] = None
    due_date: Optional[str] = None

class CalendarEventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    start_time: str
    end_time: str
    task_id: Optional[int] = None

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_iso_timestamps(cls, v):
        try:
            datetime.datetime.fromisoformat(v)
        except ValueError:
            raise ValueError("Timestamps must be in ISO format (YYYY-MM-DDTHH:MM:SS)")
        return v

class FlashcardCreate(BaseModel):
    front: str = Field(..., min_length=1, max_length=500)
    back: str = Field(..., min_length=1, max_length=2000)
    subject: Optional[str] = Field("General", max_length=100)
    image: Optional[str] = Field(None, max_length=500)
    repetitions: Optional[int] = 0
    ease_factor: Optional[float] = 2.5
    interval_days: Optional[int] = 0

class FlashcardUpdate(BaseModel):
    front: Optional[str] = Field(None, min_length=1, max_length=500)
    back: Optional[str] = Field(None, min_length=1, max_length=2000)
    subject: Optional[str] = Field(None, max_length=100)
    image: Optional[str] = Field(None, max_length=500)

class FlashcardReview(BaseModel):
    quality: int = Field(..., ge=0, le=5)

class SandboxFileOperation(BaseModel):
    file_path: str
    content: Optional[str] = None
