import datetime

def calculate_next_review(quality: int, repetitions: int, ease_factor: float, interval: int) -> dict:
    """
    Implements the SuperMemo-2 (SM-2) algorithm for spaced repetition.
    
    Parameters:
      quality (int): User rating of performance (0 to 5)
                     5: perfect response
                     4: correct response after hesitation
                     3: correct response recalled with serious difficulty
                     2: incorrect response; where the correct one seemed easy to recall
                     1: incorrect response; the correct one remembered
                     0: complete blackout
      repetitions (int): Number of consecutive successful repetitions
      ease_factor (float): The current ease factor (EF)
      interval (int): Current interval in days until the next review
      
    Returns:
      dict: Updated spaced repetition parameters:
            - next_interval: New interval in days
            - next_repetitions: New consecutive repetitions count
            - next_ease_factor: New ease factor
            - next_review_date: ISO-formatted date for the next review
    """
    # Enforce quality score bounds between 0 and 5 inclusive to prevent invalid inputs.
    quality = max(0, min(5, quality))
    
    # Update ease factor using the standard SM-2 formula:
    # EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    new_ease_factor = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    
    # Floor the ease factor at 1.3 to prevent review intervals from getting too short.
    if new_ease_factor < 1.3:
        new_ease_factor = 1.3
        
    # Round ease factor to 2 decimal places to keep calculations clean.
    new_ease_factor = round(new_ease_factor, 2)
    
    # Determine the next interval and repetitions count based on quality
    if quality < 3:
        # If quality is below 3, the response was incorrect (lapse).
        # We reset the repetitions to 0 and scheduling starts over at a 1-day interval.
        new_repetitions = 0
        new_interval = 1
    else:
        # If quality is 3 or above, the response was correct.
        # We increment the consecutive repetitions count.
        new_repetitions = repetitions + 1
        
        # Calculate new interval based on consecutive repetitions
        if new_repetitions == 1:
            # First successful review: review again tomorrow.
            new_interval = 1
        elif new_repetitions == 2:
            # Second consecutive successful review: review again in 6 days.
            new_interval = 6
        else:
            # Third or later consecutive review: multiply the current interval by the ease factor.
            new_interval = int(round(interval * ease_factor))
            
    # Calculate the next review date by adding the new interval to today's date
    today = datetime.date.today()
    next_review = today + datetime.timedelta(days=new_interval)
    next_review_date = next_review.isoformat()
    
    return {
        "next_interval": new_interval,
        "next_repetitions": new_repetitions,
        "next_ease_factor": new_ease_factor,
        "next_review_date": next_review_date
    }


def calculate_sm2(quality: int, repetitions: int, interval_days: int, ease_factor: float) -> dict:
    """
    Legacy wrapper for backward compatibility with the old calculate_sm2 function.
    """
    res = calculate_next_review(quality, repetitions, ease_factor, interval_days)
    return {
        "repetitions": res["next_repetitions"],
        "interval_days": res["next_interval"],
        "ease_factor": res["next_ease_factor"],
        "next_review_date": res["next_review_date"]
    }
