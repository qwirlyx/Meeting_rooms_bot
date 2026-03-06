import datetime


def get_moscow_now() -> datetime.datetime:
    """
    Возвращает текущее время в Москве.

    Сервер на Render, работает в UTC, поэтому
    используем смещение +3 часа относительно UTC.
    """
    return datetime.datetime.utcnow() + datetime.timedelta(hours=3)

