import asyncio
from aiogram import Bot, Dispatcher

from config import BOT_TOKEN
from database import init_db, seed_rooms
from handlers import start, booking

# Создаём экземпляр бота и диспетчера один раз на всё приложение.
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Регистрируем роутеры с хендлерами команд и логикой бронирования.
dp.include_router(start.router)
dp.include_router(booking.router)


async def main():
    """Точка входа: инициализация БД, наполнение комнатами и запуск long-polling."""
    await init_db()
    await seed_rooms()
    await dp.start_polling(bot)


if __name__ == "__main__":
    # Запускаем основной event-loop бота.
    asyncio.run(main())