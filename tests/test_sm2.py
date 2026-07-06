import unittest
import datetime
from skills.spaced_repetition.sm2 import calculate_next_review

class TestSM2SpacedRepetition(unittest.TestCase):
    
    def test_first_review(self):
        """
        Verify first review of a card (repetitions=0) with quality >= 3.
        It should reset/set next_repetitions to 1 and next_interval to 1 day.
        """
        result = calculate_next_review(quality=4, repetitions=0, ease_factor=2.5, interval=1)
        self.assertEqual(result["next_repetitions"], 1)
        self.assertEqual(result["next_interval"], 1)
        self.assertEqual(result["next_ease_factor"], 2.5) # q=4 has no change on EF
        
        # Verify review date is 1 day in the future
        expected_date = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
        self.assertEqual(result["next_review_date"], expected_date)

    def test_consecutive_good_reviews(self):
        """
        Verify consecutive successful reviews:
        - Second review (repetitions=1) -> next_interval = 6 days, repetitions = 2.
        - Third review (repetitions=2) -> next_interval = interval * ease_factor.
        """
        # Second review
        result_2nd = calculate_next_review(quality=5, repetitions=1, ease_factor=2.5, interval=1)
        self.assertEqual(result_2nd["next_repetitions"], 2)
        self.assertEqual(result_2nd["next_interval"], 6)
        self.assertEqual(result_2nd["next_ease_factor"], 2.6) # q=5 increases EF by 0.1
        
        expected_date_2nd = (datetime.date.today() + datetime.timedelta(days=6)).isoformat()
        self.assertEqual(result_2nd["next_review_date"], expected_date_2nd)

        # Third review
        result_3rd = calculate_next_review(quality=4, repetitions=2, ease_factor=2.6, interval=6)
        self.assertEqual(result_3rd["next_repetitions"], 3)
        # 6 * 2.6 = 15.6 -> rounded to 16
        self.assertEqual(result_3rd["next_interval"], 16)
        self.assertEqual(result_3rd["next_ease_factor"], 2.6) # q=4 has no change on EF
        
        expected_date_3rd = (datetime.date.today() + datetime.timedelta(days=16)).isoformat()
        self.assertEqual(result_3rd["next_review_date"], expected_date_3rd)

    def test_lapse_reset(self):
        """
        Verify that quality < 3 triggers a lapse:
        - repetitions resets to 0.
        - next_interval resets to 1 day.
        - ease factor decreases according to standard formula.
        """
        result = calculate_next_review(quality=2, repetitions=3, ease_factor=2.5, interval=16)
        self.assertEqual(result["next_repetitions"], 0)
        self.assertEqual(result["next_interval"], 1)
        
        # EF calculation: 2.5 + (0.1 - (5-2) * (0.08 + (5-2)*0.02))
        # = 2.5 + (0.1 - 3 * (0.08 + 3 * 0.02))
        # = 2.5 + (0.1 - 3 * 0.14)
        # = 2.5 + (0.1 - 0.42) = 2.18
        self.assertEqual(result["next_ease_factor"], 2.18)

    def test_ease_factor_floor(self):
        """
        Verify that ease_factor never drops below the absolute floor of 1.3.
        """
        # Start with ease_factor=1.4 and quality=0 (complete blackout, which reduces EF by 0.8)
        result = calculate_next_review(quality=0, repetitions=1, ease_factor=1.4, interval=6)
        
        # Expected formula math: 1.4 - 0.8 = 0.6. Should be floored to 1.3
        self.assertEqual(result["next_ease_factor"], 1.3)
        self.assertEqual(result["next_repetitions"], 0)
        self.assertEqual(result["next_interval"], 1)

if __name__ == "__main__":
    unittest.main()
