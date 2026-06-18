import re
import math
from datetime import date, timedelta

def estimate_reading_time(text, words_per_minute=200):
    """Simple word count / WPM reading time estimator."""
    if not text:
        return 0
    word_count = len(re.findall(r'\w+', text))
    return max(1, math.ceil(word_count / words_per_minute))

def calculate_date_range(period, start_date=None):
    """Get date range based on period (daily, weekly, monthly)."""
    if not start_date:
        start_date = date.today()
    
    if period == 'daily':
        return start_date, start_date
    elif period == 'weekly':
        # Start of week (Monday) to Sunday
        start = start_date - timedelta(days=start_date.weekday())
        end = start + timedelta(days=6)
        return start, end
    elif period == 'monthly':
        # First day to last day of the current month
        start = start_date.replace(day=1)
        next_month = start.replace(day=28) + timedelta(days=4)
        end = next_month - timedelta(days=next_month.day)
        return start, end
    return start_date, start_date
