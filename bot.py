import asyncio
from aiogram import Bot, Dispatcher

from config import BOT_TOKEN
from database import init_db, seed_rooms
from handlers import start, booking

# Добавлено для webhook (необходимые импорты для хостинга)
from aiohttp import web
from aiogram.webhook import AIOHTTPWebApp

# Создаём экземпляр бота и диспетчера один раз на всё приложение.
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Регистрируем роутеры с хендлерами команд и логикой бронирования.
dp.include_router(start.router)
dp.include_router(booking.router)

async def main():
    """Точка входа: инициализация БД, наполнение комнатами и запуск webhook для хостинга."""
    await init_db()
    await seed_rooms()

    # Настройка webhook (для работы на хостинге)
    app = web.Application()
    webhook_requests_handler = AIOHTTPWebApp(dp)
    webhook_requests_handler.register(app, path="/webhook")

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)  # Port 8080 для Render.com
    await site.start()

    # Установка webhook URL 
    webhook_url = "https://meeting-rooms-bot.onrender.com/webhook" 
    await bot.set_webhook(webhook_url)

    try:
        await asyncio.Event().wait()  # Бесконечный цикл для работы бота
    finally:
        await bot.delete_webhook()  # Очистка webhook при остановке
        await runner.cleanup()

    # Для теста:
    # await dp.start_polling(bot)

if __name__ == "__main__":
    # Запускаем основной event-loop бота.
    asyncio.run(main())

