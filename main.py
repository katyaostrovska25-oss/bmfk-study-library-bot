import os
import json
import base64
import asyncio
from aiohttp import web, ClientSession
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_REPO = os.environ["GITHUB_REPO"]
BASE_URL = os.environ["RENDER_EXTERNAL_URL"].rstrip("/")
PORT = int(os.environ.get("PORT", "10000"))
DATA_FILE = "books.json"

CATEGORIES = {
    "1": ("Гуманітарні та соціально-економічні дисципліни", [
        "Історія медицини та медсестринства",
        "Історія та культура України",
        "Українська мова за професійним спрямуванням",
    ]),
    "2": ("Загальноосвітні дисципліни", [
        "Англійська мова", "Захист України", "Хімія",
    ]),
    "3": ("Клінічні дисципліни — лікувальна справа", [
        "Акушерство і гінекологія",
        "Медична та соціальна реабілітація",
        "Неврологія",
        "Основи медсестринства. Догляд за хворими",
        "Педіатрія", "Психіатрія",
    ]),
    "4": ("Клінічні дисципліни — сестринська справа", [
        "Акушерство і гінекологія",
        "Медична та соціальна реабілітація",
        "Медсестринство в геронтології та геріатрії",
        "Медсестринство в інфектології",
        "Медсестринство в неврології",
        "Медсестринство в педіатрії",
        "Основи медсестринства. Догляд за хворими",
        "Психіатрія",
    ]),
    "5": ("Природничо-наукові дисципліни — лікувальна справа", [
        "Анатомія і фізіологія людини",
        "Медична хімія",
        "Мікробіологія з вірусологією та основами імунології",
        "Нутриціологія",
        "Основи психології міжособового спілкування",
    ]),
    "6": ("Природничо-наукові дисципліни — фармація", [
        "Техніка лабораторних робіт",
        "Технологія ліків",
        "Фармацевтична хімія",
    ]),
}

async def github_request(method, path, **kwargs):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    async with ClientSession() as session:
        async with session.request(
            method, url, headers=headers, **kwargs
        ) as response:
            data = await response.json()
            if response.status >= 400:
                raise RuntimeError(
                    f"GitHub API error {response.status}: {data}"
                )
            return data

async def load_books():
    try:
        result = await github_request("GET", DATA_FILE)
        content = base64.b64decode(result["content"]).decode("utf-8")
        return json.loads(content), result["sha"]
    except RuntimeError as error:
        if "404" in str(error):
            return [], None
        raise

async def save_book(book):
    books, sha = await load_books()
    books.append(book)
    content = base64.b64encode(
        json.dumps(books, ensure_ascii=False, indent=2).encode("utf-8")
    ).decode("ascii")
    body = {
        "message": "Add textbook through BMFK Telegram bot",
        "content": content,
    }
    if sha:
        body["sha"] = sha
    await github_request("PUT", DATA_FILE, json=body)

def category_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(name, callback_data=f"cat:{key}")]
        for key, (name, _) in CATEGORIES.items()
    ] + [[InlineKeyboardButton("🏠 Головне меню", callback_data="home")]])

def subject_keyboard(key):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(subject, callback_data=f"sub:{key}:{i}")]
        for i, subject in enumerate(CATEGORIES[key][1])
    ] + [[InlineKeyboardButton("⬅️ Назад", callback_data="categories")]])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    keyboard = [
        [InlineKeyboardButton("📚 Підручники", callback_data="categories")],
        [InlineKeyboardButton("🔎 Пошук матеріалів", callback_data="search")],
        [InlineKeyboardButton("📤 Запропонувати файл", callback_data="suggest")],
        [InlineKeyboardButton("ℹ️ Допомога", callback_data="help")],
    ]
    await update.effective_message.reply_text(
        "📚 ЕЛЕКТРОННА БІБЛІОТЕКА БМФК\n\n"
        "Оберіть потрібний розділ:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def show_subject_books(update, context, key, index):
    subject = CATEGORIES[key][1][index]
    try:
        books, _ = await load_books()
    except Exception:
        await update.effective_message.reply_text(
            "Не вдалося завантажити каталог. Спробуйте пізніше."
        )
        return

    matches = [
        b for b in books
        if b.get("category") == key and b.get("subject") == subject
    ]
    if not matches:
        await update.effective_message.reply_text(
            f"📚 {subject}\n\nПідручники ще додаються."
        )
        return

    await update.effective_message.reply_text(f"📚 {subject}")
    for book in matches:
        await update.effective_message.reply_document(
            document=book["file_id"],
            caption=book["title"],
        )

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "home":
        await start(update, context)
    elif data == "categories":
        await query.message.reply_text(
            "📚 Оберіть категорію:", reply_markup=category_keyboard()
        )
    elif data.startswith("cat:"):
        key = data.split(":")[1]
        await query.message.reply_text(
            CATEGORIES[key][0], reply_markup=subject_keyboard(key)
        )
    elif data.startswith("sub:"):
        _, key, index = data.split(":")
        await show_subject_books(update, context, key, int(index))
    elif data == "search":
        context.user_data["search_mode"] = True
        await query.message.reply_text(
            "🔎 Напишіть назву предмета або підручника для пошуку."
        )
    elif data == "suggest":
        await query.message.reply_text(
            "📤 Щоб запропонувати навчальний файл, надішліть його "
            "адміністратору бібліотеки."
        )
    elif data == "help":
        await query.message.reply_text(
            "ℹ️ Оберіть категорію, потім предмет, щоб отримати PDF.\n"
            "Для пошуку скористайтеся кнопкою «Пошук матеріалів»."
        )
    elif data.startswith("admincat:"):
        key = data.split(":")[1]
        context.user_data["upload_category"] = key
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(s, callback_data=f"adminsub:{i}")]
            for i, s in enumerate(CATEGORIES[key][1])
        ])
        await query.message.reply_text("Оберіть предмет:", reply_markup=keyboard)
    elif data.startswith("adminsub:"):

        index = int(data.split(":")[1])

        key = context.user_data.get("upload_category")

        if not key:

            await query.message.reply_text("Почніть додавання з /upload.")

            return

        context.user_data["upload_subject"] = CATEGORIES[key][1][index]

        context.user_data["awaiting_pdf"] = True

        await query.message.reply_text(

            "Тепер надішліть PDF-документ як файл (📎 → Файл)."

        )

async def upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:

        await update.effective_message.reply_text(

            "Додавати підручники може лише адміністратор."

        )

        return

    context.user_data.clear()

    await update.effective_message.reply_text(

        "Оберіть категорію для нового підручника:",

        reply_markup=InlineKeyboardMarkup([

            [InlineKeyboardButton(name, callback_data=f"admincat:{key}")]

            for key, (name, _) in CATEGORIES.items()

        ]),

    )

async def receive_document(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.user_data.get("awaiting_pdf"):

        if context.user_data.get("search_mode"):

            query = update.effective_message.text.lower()

            context.user_data["search_mode"] = False

            try:

                books, _ = await load_books()

                matches = [

                    b for b in books

                    if query in b.get("title", "").lower()

                    or query in b.get("subject", "").lower()

                ]

                if not matches:

                    await update.effective_message.reply_text(

                        "Нічого не знайдено. Спробуйте іншу назву."

                    )

                else:

                    for book in matches:

                        await update.effective_message.reply_document(

                            book["file_id"], caption=book["title"]

                        )

            except Exception:

                await update.effective_message.reply_text(

                    "Пошук тимчасово недоступний."

                )

        return

    if update.effective_user.id != ADMIN_ID:

        return

    document = update.effective_message.document

    if not document or not document.file_name.lower().endswith(".pdf"):

        await update.effective_message.reply_text(

            "Будь ласка, надішліть PDF як документ."

        )

        return

    key = context.user_data.get("upload_category")

    subject = context.user_data.get("upload_subject")

    if not key or not subject:

        await update.effective_message.reply_text(

            "Почніть додавання заново командою /upload."

        )

        return

    title = document.file_name

    book = {

        "category": key,

        "subject": subject,

        "title": title,

        "file_id": document.file_id,

    }

    try:

        await save_book(book)

        context.user_data.clear()

        await update.effective_message.reply_text(

            f"✅ Додано до бібліотеки!\nПредмет: {subject}\nФайл: {title}"

        )

    except Exception as error:

        print(f"Save error: {error}")

        await update.effective_message.reply_text(

            "Не вдалося зберегти каталог. Перевірте налаштування GitHub."

        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.effective_message.reply_text(

        "/start — головне меню\n"

        "/upload — додати підручник (лише адміністратор)\n"

        "/help — допомога"

    )

async def webhook(request):

    if request.match_info["token"] != TOKEN:

        raise web.HTTPNotFound()

    try:

        data = await request.json()

        update = Update.de_json(data, telegram_app.bot)

        await telegram_app.process_update(update)

        return web.Response(text="OK")

    except Exception as error:

        print(f"Webhook error: {error}")

        return web.Response(status=500, text="Error")

telegram_app = None

async def main():

    global telegram_app

    telegram_app = Application.builder().token(TOKEN).build()

    telegram_app.add_handler(CommandHandler("start", start))

    telegram_app.add_handler(CommandHandler("upload", upload_command))

    telegram_app.add_handler(CommandHandler("help", help_command))

    telegram_app.add_handler(CallbackQueryHandler(buttons))

    telegram_app.add_handler(

        MessageHandler(filters.Document.ALL, receive_document)

    )

    telegram_app.add_handler(

        MessageHandler(filters.TEXT & ~filters.COMMAND, receive_document)

    )

    await telegram_app.initialize()

    await telegram_app.start()

    server = web.Application()

    server.router.add_post("/{token}", webhook)

    runner = web.AppRunner(server)

    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", PORT)

    await site.start()

    await telegram_app.bot.set_webhook(f"{BASE_URL}/{TOKEN}")

    print(f"Bot running on port {PORT}")

    try:

        await asyncio.Event().wait()

    finally:

        await runner.cleanup()

        await telegram_app.stop()

        await telegram_app.shutdown()

if __name__ == "__main__":

    asyncio.run(main())
