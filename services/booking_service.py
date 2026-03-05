import datetime


def generate_slots(date):
    now = datetime.datetime.now()
    is_today = date == now.date()
    start_hour = 9
    if is_today:
        current_hour = now.hour
        # Для сегодняшнего дня показываем текущее окно, если оно ещё не закончилось
        start_hour = max(9, current_hour)

    end_hour = 18  # Рабочий день до 18:00
    slots = []
    for hour in range(start_hour, end_hour):
        start = datetime.datetime.combine(date, datetime.time(hour, 0))
        end = start + datetime.timedelta(hours=1)
        # Пропускаем только полностью прошедшие слоты
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