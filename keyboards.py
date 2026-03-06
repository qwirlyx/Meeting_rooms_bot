from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import datetime  # Добавь это
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏢 Забронировать комнату")],
            [KeyboardButton(text="📅 Мои бронирования")],
            [KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="🧹 Очистить историю")],
            [KeyboardButton(text="👥 Пригласить друга")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие"
    )
    return keyboard
    
def rooms_keyboard(rooms):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{room[1]} ({room[2]} чел.)",
                    callback_data=f"room_{room[0]}"
                )
            ]
            for room in rooms
        ]
    )
    return keyboard

def date_keyboard():
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            # «Сегодня» — специальное значение, дата подставляется в момент нажатия
            [InlineKeyboardButton(text="Сегодня", callback_data="date_today")],
            [InlineKeyboardButton(text="Завтра", callback_data=f"date_{tomorrow.isoformat()}")],
            [InlineKeyboardButton(text="Выбрать дату", callback_data="date_custom")]
        ]
    )
    return keyboard

def slots_keyboard(slots, room_id, date):
    buttons = []
    now = datetime.datetime.now()
    today = now.date()

    for start, end, is_free in slots:
        # Для «сегодня» не показываем слоты, которые уже полностью прошли
        if date == today and end <= now:
            continue

        time_str = f"{start.strftime('%H:%M')}–{end.strftime('%H:%M')}"
        emoji = "🟢" if is_free else "🔴"

        # Для текущего свободного окна сегодня показываем, что оно ещё доступно до конца часа
        if is_free and date == today and start <= now < end:
            label = f"{time_str} {emoji} (окно свободно до {end.strftime('%H:%M')})"
        else:
            label = f"{time_str} {emoji}"

        data = f"slot_{room_id}_{date.isoformat()}_{start.hour}" if is_free else "slot_busy"
        buttons.append([InlineKeyboardButton(text=label, callback_data=data)])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def my_bookings_keyboard(bookings):
    """Клавиатура со списком броней и кнопками отмены"""
    if not bookings:
        return None

    buttons = []
    for booking_id, room_name, start_iso, end_iso in bookings:
        start = datetime.datetime.fromisoformat(start_iso)
        end = datetime.datetime.fromisoformat(end_iso)
        text = f"{room_name} {start.strftime('%d.%m %H:%M')}–{end.strftime('%H:%M')}"
        callback = f"cancel_{booking_id}"
        buttons.append([InlineKeyboardButton(text=f"❌ {text}", callback_data=callback)])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)
