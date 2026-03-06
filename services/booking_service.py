import datetime


def generate_slots(date):
    now = datetime.datetime.now()
    is_today = date == now.date()

    start_hour = 9
    end_hour = 18  # Рабочий день до 18:00

    # Если текущее время >= 18:00 и is_today, нет слотов — рабочий день окончен
    if is_today and now.hour >= end_hour:
        return []

    slots = []
    for hour in range(start_hour, end_hour):
        start = datetime.datetime.combine(date, datetime.time(hour, 0))
        end = start + datetime.timedelta(hours=1)

        # Для сегодняшнего дня полностью прошедшие интервалы не показываем,
        # но если сейчас внутри слота (окно ещё идёт) — он остаётся доступным.
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
