import datetime

def calculate_priority_score(importance: int, urgency: int, due_date: str = None) -> dict:
    """
    Calculates task priority score and maps it to an Eisenhower matrix quadrant.
    
    Parameters:
      importance (int): Value from 1 to 5.
      urgency (int): Value from 1 to 5.
      due_date (str): ISO date string (YYYY-MM-DD), optional.
      
    Returns:
      dict: Updated priority score (0.0 to 5.0) and Eisenhower quadrant (Q1-Q4).
    """
    # Enforce bounds
    importance = max(1, min(5, importance))
    urgency = max(1, min(5, urgency))
    
    # Calculate time factor
    time_factor = 0.0
    if due_date:
        try:
            due = datetime.date.fromisoformat(due_date)
            today = datetime.date.today()
            delta = (due - today).days
            
            if delta <= 0:
                time_factor = 1.0
            elif delta >= 14:
                time_factor = 0.0
            else:
                time_factor = 1.0 - (delta / 14.0)
        except ValueError:
            time_factor = 0.0
            
    # Compute score (scale of 1 to 5)
    # importance and urgency are on scale 1-5, time_factor is on scale 0-1 (we multiply by 5 to align scales)
    score = (importance * 0.45) + (urgency * 0.35) + ((time_factor * 5.0) * 0.20)
    score = round(score, 2)
    
    # Determine Eisenhower matrix quadrant
    if importance >= 3 and urgency >= 3:
        quadrant = "Q1: Do First"
    elif importance >= 3 and urgency < 3:
        quadrant = "Q2: Schedule"
    elif importance < 3 and urgency >= 3:
        quadrant = "Q3: Delegate/Optimize"
    else:
        quadrant = "Q4: Eliminate"
        
    return {
        "score": score,
        "quadrant": quadrant
    }
