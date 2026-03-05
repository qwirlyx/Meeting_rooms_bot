from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart
from database import get_all_rooms
from keyboards import rooms_keyboard, main_menu_keyboard  # ← добавь main_menu_keyboard

router = Router()

@router.message(CommandStart())
async def start_handler(message: Message):
    rooms = await get_all_rooms()
    if not rooms:
        await message.answer("Нет комнат в базе. Проверьте seed_rooms.")
        return

    user = message.from_user
    display_name = user.first_name or user.username or "гость"

    await message.answer(
        f"{display_name}, Приветствую!\n\n"
        "🏢 Добро пожаловать в систему бронирования переговорных!\n\n"
        "Выберите действие внизу или нажмите кнопку:",
        reply_markup=main_menu_keyboard()  
    )