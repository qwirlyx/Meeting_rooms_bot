import datetime
from zoneinfo import ZoneInfo  

# Московская таймзона (официальная для России)
MOSCOW_TZ = ZoneInfo("Europe/Moscow")

def generate_slots(date: datetime.date):
    """Генерирует слоты 9:00–18:00 по московскому времени."""
    # Теперь now всегда по Москве!
    now = datetime.datetime.now(MOSCOW_TZ)
    
    is_today = date == now.date()
    start_hour = 9
    end_hour = 18

    # Если сегодня и уже после 18:00 по Москве — нет слотов
    if is_today and now.hour >= end_hour:
        return []

    # Если сегодня — начинаем со следующего часа (или с 9:00)
    if is_today:
        current_hour = now.hour
        start_hour = max(9, current_hour + 1)

    # Если start_hour уже >= end_hour — слотов нет (на всякий случай)
    if start_hour >= end_hour:
        return []

    slots = []
    for hour in range(start_hour, end_hour):
        start = datetime.datetime.combine(date, datetime.time(hour, 0))
        end = start + datetime.timedelta(hours=1)

        # Для сегодня пропускаем уже прошедшие слоты
        if is_today and end <= now:
            continue

        slots.append((start, end))

    return slots


async def get_available_slots(room_id, date):
    from database import get_bookings_for_room_date  # Импорт здесь, чтобы избежать цикла

    bookings = await get_bookings_for_room_date(room_id, date)
    slots = generate_slots(date)
    available = []
    for start, end in slots:
        is_free = True
        for b_start, b_end in bookings:
            if not (end <= b_start or start >= b_end):
                is_free = False
                break
        available.append((start, end, is_free))
    return available
