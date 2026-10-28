import os
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
    await update.message.reply_text(
        "📚 БІБЛІОТЕКА БМФК\n\n"
        "Вітаю! Тут збиратимемо навчальні матеріали "
        "для студентів Бериславського медичного фахового коледжу.\n\n"
        "Оберіть потрібний розділ:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "📚 Каталог підручників\n\n"
        "Бібліотека готується до наповнення.\n"
        "Незабаром тут з'являться підручники та посібники."
    )

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "🔎 Пошук матеріалів поки налаштовується."
    )

async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "📤 Щоб запропонувати навчальний файл, "
        "поки зверніться до адміністратора бібліотеки."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "ℹ️ Як користуватися бібліотекою:\n"
        "/start — відкрити меню\n"
        "/books — переглянути підручники\n"
        "/search — пошук матеріалів\n"
        "/upload — запропонувати файл\n"
        "/help — допомога"
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "books":
        await query.message.reply_text(
            "📚 Каталог підручників поки наповнюється."
        )
    elif query.data == "search":
        await query.message.reply_text(
            "🔎 Пошук матеріалів поки налаштовується."
        )
    elif query.data == "upload":
        await query.message.reply_text(
            "📤 Для додавання файлів зверніться до адміністратора."
        )
    elif query.data == "help":
        await query.message.reply_text(
            "Натисніть «Підручники», щоб переглянути каталог."
        )

def main():
    if not TOKEN:
        raise RuntimeError("Не задано змінну BOT_TOKEN")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("books", books))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("upload", upload))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    port = int(os.environ.get("PORT", "10000"))
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=f"{os.environ['RENDER_EXTERNAL_URL']}/{TOKEN}",
    )

if __name__ == "__main__":
    main()
