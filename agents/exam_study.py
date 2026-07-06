import json
from google.adk.agents import Agent
from agents.base import subagent_model
from skills.spaced_repetition.sm2 import calculate_next_review

def schedule_flashcard_review(quality: int, repetitions: int, interval_days: int, ease_factor: float) -> str:
    """
    Schedules the next review date for a flashcard using the SM-2 algorithm.
    
    Parameters:
      quality (int): Score from 0 to 5 of how well the user remembered the flashcard.
      repetitions (int): Number of consecutive successful reviews.
      interval_days (int): Current interval in days.
      ease_factor (float): Current ease factor value.
    """
    res = calculate_next_review(
        quality=quality,
        repetitions=repetitions,
        ease_factor=ease_factor,
        interval=interval_days
    )
    result = {
        "repetitions": res["next_repetitions"],
        "interval_days": res["next_interval"],
        "ease_factor": res["next_ease_factor"],
        "next_review_date": res["next_review_date"],
        "next_repetitions": res["next_repetitions"],
        "next_interval": res["next_interval"],
        "next_ease_factor": res["next_ease_factor"]
    }
    return json.dumps(result)

exam_study_agent = Agent(
    name="ExamStudyAgent",
    model=subagent_model,
    instruction=(
        "You are the Exam Study Agent. Your job is to generate study plans, flashcards, and quizzes "
        "and schedule flashcard reviews using the 'schedule_flashcard_review' tool.\n\n"
        "When generating flashcards, adhere to these quality rules:\n"
        "- Do NOT split sequential steps or list items (e.g., step 5 as question, step 6 as answer). They must form a complete Q&A pair.\n"
        "- The 'front' must be a clear, specific question, prompt, or term to define (e.g., 'What is the purpose of preprocessing in a data pipeline?').\n"
        "- The 'back' must be the direct, concise answer to the question on the front.\n"
        "- Do NOT prefix questions or answers with arbitrary sequential numbers (like '1.', '2.', '5.') unless they describe a count (e.g., '3 main steps').\n"
        "- Ensure the cards test active recall effectively.\n\n"
        "Always respond with clean structured JSON based on the user's intent. "
        "Return a JSON list of objects containing 'front' and 'back' fields."
    ),
    tools=[schedule_flashcard_review]
)
