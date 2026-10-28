import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

TOKEN = os.environ.get("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📚 Підручники", callback_data="books")],
        [InlineKeyboardButton("🔎 Пошук матеріалів", callback_data="search")],
        [InlineKeyboardButton("📤 Запропонувати файл", callback_data="upload")],
        [InlineKeyboardButton("ℹ️ Допомога", callback_data="help")],
    ]
    await update.effective_message.reply_text(
        "📚 БІБЛІОТЕКА БМФК\n\n"
        "Вітаю! Тут збиратимемо навчальні матеріали "
        "для студентів Бериславського медичного фахового коледжу.\n\n"
        "Оберіть потрібний розділ:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "📚 Каталог підручників поки наповнюється."
    )

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "🔎 Пошук матеріалів поки налаштовується."
    )

async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "📤 Для додавання файлів зверніться до адміністратора."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "ℹ️ Команди бібліотеки:\n"
        "/start — меню\n"
        "/books — підручники\n"
        "/search — пошук\n"
        "/upload — запропонувати файл\n"
        "/help — допомога"
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "books":
        await books(update, context)
    elif query.data == "search":
        await search(update, context)
    elif query.data == "upload":
        await upload(update, context)
    elif query.data == "help":
        await help_command(update, context)

async def main():
    if not TOKEN:
        raise RuntimeError("Не задано змінну BOT_TOKEN")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("books", books))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("upload", upload))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
