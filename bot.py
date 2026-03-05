import asyncio
from aiogram import Bot, Dispatcher

from config import BOT_TOKEN
from database import init_db, seed_rooms
from handlers import start, booking

# Добавлено для webhook (для Render)
from aiohttp import web
from aiogram.types import Update  # Добавлено для Update

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

    # Настройка webhook для aiogram 3.x
    async def handle_webhook(request):
        text = await request.text()
        update = Update.model_validate_json(text)  # Исправлено на model_validate_json
        await dp.feed_update(bot, update)
        return web.Response()

    app = web.Application()
    app.router.add_post('/webhook', handle_webhook)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)  # Port 8080 для Render
    await site.start()

    # Установка webhook URL (твой app — meeting-rooms-bot)
    webhook_url = "https://meeting-rooms-bot.onrender.com/webhook"
    await bot.set_webhook(webhook_url)

    try:
        await asyncio.Event().wait()  # Бесконечный цикл для работы
    finally:
        await bot.delete_webhook()
        await runner.cleanup()

    # Старый polling (раскомментируй для локального теста)
    # await dp.start_polling(bot)

if __name__ == "__main__":
    # Запускаем основной event-loop бота.
    asyncio.run(main())
