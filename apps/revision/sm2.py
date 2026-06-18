class SM2Algorithm:
    @staticmethod
    def calculate(quality_score, repetitions, easiness_factor, current_interval):
        """
        SM-2 Spaced Repetition algorithm calculation.
        
        Args:
            quality_score (int): Recall quality 0-5.
                5 - perfect response
                4 - correct response after hesitation
                3 - correct response recalled with serious difficulty
                2 - incorrect response; where the correct one seemed easy to recall
                1 - incorrect response; the correct one remembered
                0 - complete blackout, not recallable
            repetitions (int): Number of consecutive correct reviews.
            easiness_factor (float): Easiness factor EF (min 1.3).
            current_interval (int): Current spacing interval in days.
            
        Returns:
            dict: {
                'repetitions': new_repetitions,
                'easiness_factor': new_easiness_factor,
                'interval_days': new_interval_days
            }
        """
        # Ensure input values are correct type/limits
        q = int(quality_score)
        rep = int(repetitions)
        ef = float(easiness_factor)
        interval = int(current_interval)

        # 1. Update Easiness Factor (EF)
        # EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        ef = ef + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        if ef < 1.3:
            ef = 1.3

        # 2. Update Repetitions & Interval Days
        if q >= 3:
            # Correct answer
            if rep == 0:
                new_interval = 1
            elif rep == 1:
                new_interval = 6
            else:
                new_interval = int(round(interval * ef))
            rep += 1
        else:
            # Incorrect answer
            rep = 0
            new_interval = 1

        return {
            'repetitions': rep,
            'easiness_factor': round(ef, 2),
            'interval_days': new_interval
        }
