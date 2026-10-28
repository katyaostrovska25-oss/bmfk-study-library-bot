import os
import asyncio
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

TOKEN = os.environ.get("BOT_TOKEN")
BASE_URL = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
PORT = int(os.environ.get("PORT", "10000"))

telegram_app = None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📚 Підручники", callback_data="books")],
        [InlineKeyboardButton("🔎 Пошук матеріалів", callback_data="search")],
        [InlineKeyboardButton("📤 Запропонувати файл", callback_data="upload")],
        [InlineKeyboardButton("ℹ️ Допомога", callback_data="help")],
    ]
    await update.effective_message.reply_text(
        "📚 БІБЛІОТЕКА БМФК\n\n"
        "Вітаю! Навчальна бібліотека для студентів "
        "Бериславського медичного фахового коледжу.\n\n"
        "Оберіть потрібний розділ:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "📚 Каталог підручників поки наповнюється."
    )


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "🔎 Пошук навчальних матеріалів поки налаштовується."
    )


async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "📤 Додавання навчальних файлів скоро буде доступне."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "ℹ️ Команди бібліотеки:\n"
        "/start — відкрити меню\n"
        "/books — підручники\n"
        "/search — пошук матеріалів\n"
        "/upload — запропонувати файл\n"
        "/help — допомога"
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    handlers = {
        "books": books,
        "search": search,
        "upload": upload,
        "help": help_command,
    }
    handler = handlers.get(query.data)
    if handler:
        await handler(update, context)


async def webhook(request):
    if request.match_info["token"] != TOKEN:
        raise web.HTTPNotFound()

    try:
        data = await request.json()
        update = Update.de_json(data, telegram_app.bot)
        await telegram_app.process_update(update)
        return web.Response(text="OK")
    except Exception as exc:
        print(f"Webhook error: {exc}")
        return web.Response(status=500, text="Webhook error")


async def main():
    global telegram_app

    if not TOKEN:
        raise RuntimeError("BOT_TOKEN is missing in Environment Variables")
    if not BASE_URL:
        raise RuntimeError("RENDER_EXTERNAL_URL is missing")

    telegram_app = Application.builder().token(TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("books", books))
    telegram_app.add_handler(CommandHandler("search", search))
    telegram_app.add_handler(CommandHandler("upload", upload))
    telegram_app.add_handler(CommandHandler("help", help_command))
    telegram_app.add_handler(CallbackQueryHandler(button_handler))

    await telegram_app.initialize()
    await telegram_app.bot.set_webhook(f"{BASE_URL}/{TOKEN}")
    await telegram_app.start()

    server = web.Application()
    server.router.add_post("/{token}", webhook)

    runner = web.AppRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    print(f"Library bot is running on port {PORT}")

    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()
        await telegram_app.stop()
        await telegram_app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
