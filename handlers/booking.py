from zoneinfo import ZoneInfo
MOSCOW_TZ = ZoneInfo("Europe/Moscow")
from aiogram import Router
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram import F
from aiogram.filters import Command

# Импорты из других модулей проекта
from database import (
    get_room_by_id,
    get_all_rooms,
    create_booking,
    get_user_bookings,
    delete_booking,
    clear_bookings,
    get_stats,
    find_overlap_interval,
)
from keyboards import (
    date_keyboard,
    slots_keyboard,
    my_bookings_keyboard,
    rooms_keyboard,
    main_menu_keyboard  
)
from services.booking_service import get_available_slots

import datetime

router = Router()

# ────────────────────────────────────────────────
#               Состояния FSM
# ────────────────────────────────────────────────

class BookingState(StatesGroup):
    room_selected = State()
    date_selected = State()
    slot_selected = State()

# ────────────────────────────────────────────────
#               Выбор комнаты → Фото + дата
# ────────────────────────────────────────────────

@router.callback_query(F.data.startswith("room_"))
async def show_room_info(callback: CallbackQuery, state: FSMContext):
    room_id = int(callback.data.split("_")[1])
    room = await get_room_by_id(room_id)

    if not room:
        await callback.message.answer("Комната не найдена.")
        await callback.answer()
        return

    await callback.message.answer_photo(
        photo=FSInputFile(room[3]),
        caption=(
            f"🏢 **{room[1]}**\n"
            f"👥 Вместимость: {room[2]} чел.\n\n"
            f"{room[4]}"
        ),
        reply_markup=date_keyboard(),
        parse_mode="Markdown",
    )

    await state.set_state(BookingState.room_selected)
    await state.update_data({"room_id": room_id})
    await callback.answer()

# ────────────────────────────────────────────────
#               Выбор даты
# ────────────────────────────────────────────────

@router.callback_query(F.data.startswith("date_"))
async def select_date(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    room_id = data.get("room_id")

    if not room_id:
        await callback.answer("Ошибка: комната не выбрана.")
        return

    if callback.data == "date_custom":
        await callback.message.answer(
            "Введите необходимую дату в формате:\n"
            "DD.MM.YYYY"
        )
        await state.set_state(BookingState.date_selected)
        await callback.answer()
        return

    date_str = callback.data.split("_")[1]
    date = datetime.date.fromisoformat(date_str)

    today_msk = datetime.datetime.now(MOSCOW_TZ).date()
    if date < today_msk:
        await callback.message.answer("❌ Нельзя бронировать прошедшие даты.")
        await callback.answer()
        return

    await show_slots(callback, state, room_id, date)
    await callback.answer()


@router.message(BookingState.date_selected)
async def process_custom_date(message: Message, state: FSMContext):
    try:
        text = message.text.strip()
        try:
            date = datetime.datetime.strptime(text, "%d.%m.%Y").date()
        except ValueError:
            date = datetime.date.fromisoformat(text)

        today_msk = datetime.datetime.now(MOSCOW_TZ).date()
        if date < today_msk:
            await message.answer("❌ Нельзя бронировать прошедшие даты.")
            return

        data = await state.get_data()
        room_id = data.get("room_id")
        await show_slots(message, state, room_id, date)

    except ValueError:
        await message.answer("Неверный формат даты. Попробуйте DD.MM.YYYY или YYYY-MM-DD.")

# ────────────────────────────────────────────────
#               Показ слотов + проверка доступности
# ────────────────────────────────────────────────

async def show_slots(event, state: FSMContext, room_id: int, date: datetime.date):
    slots = await get_available_slots(room_id, date)
    print(f"DEBUG: date={date}, slots_count={len(slots)}")  # оставляем для отладки

    if not slots:
        msg_text = (
            "❌ Нет доступных слотов на эту дату\n"
            "(рабочий день окончен или время уже прошло)"
        )
        keyboard = date_keyboard()
        
        if isinstance(event, Message):
            await event.reply(msg_text, reply_markup=keyboard)
        else:
            await event.message.answer(msg_text, reply_markup=keyboard)
        
        await callback.answer()  # если event — это callback (на всякий случай)
        return

    keyboard = slots_keyboard(slots, room_id, date)
    msg_text = "Выберите удобный слот:"

    if isinstance(event, Message):
        await event.reply(msg_text, reply_markup=keyboard)
    else:
        await event.message.answer(msg_text, reply_markup=keyboard)

    await state.set_state(BookingState.slot_selected)
    await state.update_data({"date": date})

    # Если event — это CallbackQuery — обязательно отвечаем, чтобы убрать "часики"
    if hasattr(event, 'answer'):
        await event.answer()

# ────────────────────────────────────────────────
#               Подтверждение бронирования
# ────────────────────────────────────────────────

@router.callback_query(F.data.startswith("slot_"))
async def select_slot(callback: CallbackQuery, state: FSMContext):
    if callback.data == "slot_busy":
        await callback.answer("Этот слот занят.")
        return

    # Парсинг callback_data
    try:
        _, room_id_str, date_str, hour_str = callback.data.split("_")
        room_id = int(room_id_str)
        hour = int(hour_str)
        date = datetime.date.fromisoformat(date_str)
    except (ValueError, IndexError):
        await callback.answer("Ошибка в данных кнопки.")
        return

    start = datetime.datetime.combine(date, datetime.time(hour, 0))
    end = start + datetime.timedelta(hours=1)

    # Проверяем, что состояние соответствует выбранному слоту
    data = await state.get_data()
    if data.get("room_id") != room_id or data.get("date") != date:
        await callback.answer("Ошибка: данные сессии не совпадают.")
        return

    # Пытаемся создать бронь
    success = await create_booking(room_id, callback.from_user.id, start, end)

    if success:
        await callback.message.answer(
            "**✅ Бронирование подтверждено!**\n"
            f"**{start.strftime('%H:%M')} – {end.strftime('%H:%M')}**\n"
            f"*{date.strftime('%d.%m.%Y')}*\n"
            "Желаем вам успешных переговоров 😎",
            parse_mode="Markdown"
        )
        await state.clear()
    else:
        # Пытаемся понять, почему не удалось
        overlap = await find_overlap_interval(room_id, start, end)
        if overlap:
            busy_start, busy_end = overlap
            await callback.message.answer(
                "❌ Комната уже занята.\n"
                f"Занята с {busy_start.strftime('%H:%M')} до {busy_end.strftime('%H:%M')}.\n"
                "Ваш интервал пересекается с существующим бронированием."
            )
        else:
            await callback.message.answer("❌ Этот слот уже занят (конфликт).")

        # Предлагаем ближайший свободный слот после выбранного
        slots = await get_available_slots(room_id, date)
        alt_slots = [s for s in slots if s[2] and s[0] > start]

        if alt_slots:
            alt_start, alt_end, _ = alt_slots[0]
            await callback.message.answer(
                "Но есть свободная альтернатива:\n"
                f"🕒 {alt_start.strftime('%H:%M')} – {alt_end.strftime('%H:%M')}\n"
                "Забронировать этот слот?",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[
                        InlineKeyboardButton(
                            text="Да, забронировать",
                            callback_data=f"slot_{room_id}_{date.isoformat()}_{alt_start.hour}"
                        )
                    ]]
                )
            )
            # state НЕ очищаем — оставляем room_id и date
        else:
            await state.clear()

    await callback.answer()

# ────────────────────────────────────────────────
#               Команды и кнопки главного меню
# ────────────────────────────────────────────────

@router.message(F.text == "🏢 Забронировать комнату")
async def book_room_button(message: Message):
    rooms = await get_all_rooms()
    if not rooms:
        await message.answer("Нет доступных комнат в базе.")
        return

    await message.answer(
        "Выберите переговорную комнату:",
        reply_markup=rooms_keyboard(rooms)
    )


@router.message(F.text == "🧹 Очистить историю")
async def clear_history_button(message: Message):
    # Пытаемся удалить последние сообщения в чате, чтобы "почистить" историю для пользователя
    chat_id = message.chat.id
    current_id = message.message_id

    for msg_id in range(current_id, max(current_id - 50, 0), -1):
        try:
            await message.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except Exception:
            # Игнорируем ошибки удаления (сообщение слишком старое и т.п.)
            continue

    rooms = await get_all_rooms()
    if not rooms:
        await message.answer("Нет доступных комнат в базе.")
        return

    user = message.from_user
    display_name = user.first_name or user.username or "гость"

    # После "очистки" отправляем приветствие и сразу показываем выбор комнаты
    await message.answer(
        f"{display_name}, рад вас видеть вновь в нашей системе бронирования переговорных комнат!\n\n"
        "Выберите переговорную комнату ниже.\n\n"
        "Если хотите использовать другие функции бота — выберите действие внизу, нажав на кнопку в меню.",
        reply_markup=rooms_keyboard(rooms),
    )


@router.message(F.text == "📅 Мои бронирования")
async def my_bookings_button(message: Message):
    bookings = await get_user_bookings(message.from_user.id)

    if not bookings:
        await message.answer("У вас пока нет активных броней.")
        return

    text = "Ваши текущие брони:\n\n"
    for _, room_name, start_iso, end_iso in bookings:
        start = datetime.datetime.fromisoformat(start_iso)
        end = datetime.datetime.fromisoformat(end_iso)
        text += f"• {room_name}   {start.strftime('%d.%m.%Y %H:%M')} – {end.strftime('%H:%M')}\n"

    keyboard = my_bookings_keyboard(bookings)
    await message.answer(text, reply_markup=keyboard)


@router.message(F.text == "📊 Статистика")
@router.message(Command("stats"))
async def stats_handler(message: Message):
    popular_room, room_count, busiest_hour, hour_count = await get_stats()

    if not popular_room and not busiest_hour:
        await message.answer("Пока нет данных для статистики — ещё не было ни одной брони.")
        return

    lines = ["📊 Мини-статистика по бронированиям:"]

    if popular_room:
        lines.append(f"• Самая популярная комната: {popular_room} ({room_count} бронирований)")

    if busiest_hour:
        lines.append(f"• Самое загруженное время: {busiest_hour}:00 ({hour_count} бронирований)")

    await message.answer("\n".join(lines))


@router.message(F.text == "👥 Пригласить друга")
async def invite_button(message: Message):
    bot_username = (await message.bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start=ref_{message.from_user.id}"
    await message.answer(
        f"Поделитесь этой ссылкой с коллегами:\n"
        f"{ref_link}\n\n"
        "Спасибо, что помогаете распространять удобный инструмент! 🚀"
    )


@router.message(Command("clear_bookings"))
async def clear_bookings_handler(message: Message):
    if message.from_user.id != 1054191782:
        await message.answer("❌ Эта команда доступна только администратору.")
        return

    await clear_bookings(message.from_user.id)
    await message.answer("✅ Все ваши брони успешно очищены.")


@router.message(Command("my_bookings"))
async def my_bookings_command(message: Message):
    # Просто перенаправляем на кнопку — чтобы команда тоже работала
    await my_bookings_button(message)


@router.callback_query(F.data.startswith("cancel_"))
async def cancel_booking(callback: CallbackQuery):
    try:
        booking_id = int(callback.data.split("_")[1])
    except (ValueError, IndexError):
        await callback.answer("Ошибка в данных брони.")
        return

    success = await delete_booking(booking_id, callback.from_user.id)

    if success:
        await callback.message.edit_text(
            f"{callback.message.text}\n\n✅ Бронь успешно отменена.",
            reply_markup=None
        )
        await callback.answer("Бронь отменена")
    else:

        await callback.answer("Не удалось отменить бронь (возможно, уже удалена)")




