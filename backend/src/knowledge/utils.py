

def estimate_reading_time(text: str, wpm: int = 200) -> int:
    """
    Рассчитывает примерное время прочтения текста в минутах
    """

    words = len(text.split())
    return max(1, round(words / wpm))
