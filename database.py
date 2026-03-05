import aiosqlite
import datetime

# Имя файла SQLite-базы данных для приложения.
DB_NAME = "database.db"


async def init_db():
    """Создаёт таблицы rooms и bookings, если их ещё нет."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS rooms (
                id INTEGER PRIMARY KEY,
                name TEXT,
                capacity INTEGER,
                photo TEXT,
                description TEXT
            )
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY,
                room_id INTEGER,
                user_id INTEGER,
                start_time TEXT,
                end_time TEXT
            )
            """
        )

        await db.commit()


async def seed_rooms():
    """
    Заполняет таблицу rooms начальными данными, если она ещё пустая.
    Это удобно для демонстрации и локальной разработки.
    """
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM rooms")
        count = await cursor.fetchone()

        if count[0] == 0:
            await db.execute(
                """
                INSERT INTO rooms (name, capacity, photo, description)
                VALUES
                ('Glass Room', 9, 'images/small.jpg',
                 'Современная переговорная со стеклянными стенами. Идеально для командных встреч.'),

                ('Loft Room', 9, 'images/big.jpg',
                 'Переговорная в стиле loft с кирпичной стеной и массивным деревянным столом.'),

                ('Coworking Room', 5, 'images/coworking.jpg',
                 'Уютное пространство с красным ковром, диваном и креслами. Подходит для небольших встреч.')
                """
            )
            await db.commit()


async def get_room_by_id(room_id):
    """Возвращает полную информацию о комнате по её id."""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT * FROM rooms WHERE id = ?",
            (room_id,),
        )
        return await cursor.fetchone()


async def get_all_rooms():
    """Возвращает список всех комнат."""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT * FROM rooms")
        return await cursor.fetchall()


async def get_bookings_for_room_date(room_id, date):
    """
    Возвращает все брони для комнаты на конкретную дату в виде пар datetime.
    Используется при построении доступных слотов.
    """
    async with aiosqlite.connect(DB_NAME) as db:
        start_date = date.strftime("%Y-%m-%d 00:00:00")
        end_date = (date + datetime.timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")
        cursor = await db.execute(
            "SELECT start_time, end_time FROM bookings WHERE room_id = ? AND start_time >= ? AND start_time < ?",
            (room_id, start_date, end_date),
        )
        rows = await cursor.fetchall()
        return [
            (datetime.datetime.fromisoformat(r[0]), datetime.datetime.fromisoformat(r[1]))
            for r in rows
        ]


async def check_overlap(room_id, new_start, new_end):
    """
    Проверяет, есть ли пересечение нового интервала с уже существующими бронями.
    Логика:
        WHERE room_id = ?
          AND start_time < new_end
          AND end_time > new_start
    """
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT id FROM bookings WHERE room_id = ? AND start_time < ? AND end_time > ?",
            (room_id, new_end.isoformat(), new_start.isoformat()),
        )
        return await cursor.fetchone() is not None


async def find_overlap_interval(room_id, new_start, new_end):
    """
    Возвращает первый пересекающийся интервал (start_time, end_time) для заданной комнаты
    или None, если пересечений нет.
    """
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """
            SELECT start_time, end_time
            FROM bookings
            WHERE room_id = ?
              AND start_time < ?
              AND end_time > ?
            ORDER BY start_time
            LIMIT 1
            """,
            (room_id, new_end.isoformat(), new_start.isoformat()),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return datetime.datetime.fromisoformat(row[0]), datetime.datetime.fromisoformat(row[1])


async def create_booking(room_id, user_id, start, end):
    """
    Пытается создать бронь.
    Возвращает False, если найдено пересечение во времени, иначе создаёт запись и возвращает True.
    """
    if await check_overlap(room_id, start, end):
        return False
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO bookings (room_id, user_id, start_time, end_time) VALUES (?, ?, ?, ?)",
            (room_id, user_id, start.isoformat(), end.isoformat()),
        )
        await db.commit()
    return True


async def clear_bookings(user_id):
    """Удаляет все брони конкретного пользователя (админская утилита)."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM bookings WHERE user_id = ?", (user_id,))
        await db.commit()


async def get_user_bookings(user_id):
    """
    Возвращает список всех броней пользователя:
    (booking_id, room_name, start_time_iso, end_time_iso).
    """
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """
            SELECT b.id, r.name, b.start_time, b.end_time
            FROM bookings b
            JOIN rooms r ON b.room_id = r.id
            WHERE b.user_id = ?
            ORDER BY b.start_time ASC
            """,
            (user_id,),
        )
        rows = await cursor.fetchall()
        return rows


async def delete_booking(booking_id, user_id):
    """Удаляет бронь по id, только если она принадлежит этому пользователю."""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "DELETE FROM bookings WHERE id = ? AND user_id = ?",
            (booking_id, user_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_stats():
    """
    Возвращает простую статистику по всем бронированиям:
    - Самая популярная комната (name, count)
    - Самое загруженное время (hour_str, count)
    Если данных нет, соответствующие значения будут None.
    """
    async with aiosqlite.connect(DB_NAME) as db:
        # Самая популярная комната по количеству броней
        cursor_room = await db.execute(
            """
            SELECT r.name, COUNT(*) as cnt
            FROM bookings b
            JOIN rooms r ON b.room_id = r.id
            GROUP BY b.room_id
            ORDER BY cnt DESC
            LIMIT 1
            """
        )
        popular_room_row = await cursor_room.fetchone()

        # Самое загруженное время (по часу начала)
        cursor_hour = await db.execute(
            """
            SELECT strftime('%H', start_time) as hour, COUNT(*) as cnt
            FROM bookings
            GROUP BY hour
            ORDER BY cnt DESC
            LIMIT 1
            """
        )
        busiest_hour_row = await cursor_hour.fetchone()

    popular_room = None
    room_count = 0
    if popular_room_row:
        popular_room, room_count = popular_room_row[0], popular_room_row[1]

    busiest_hour = None
    hour_count = 0
    if busiest_hour_row:
        busiest_hour, hour_count = busiest_hour_row[0], busiest_hour_row[1]

    return popular_room, room_count, busiest_hour, hour_count