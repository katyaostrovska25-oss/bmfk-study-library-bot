import os 
import json 
import base64 
import asyncio 
import uuid 
from urllib.parse import urlsplit

from aiohttp import web, ClientSession 
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup 
from telegram.ext import ( 
Application, 
CommandHandler, 
CallbackQueryHandler,
MessageHandler, 
ContextTypes, 
filters, 
)
TOKEN = os.environ["BOT_TOKEN"] 
ADMIN_ID = int(os.environ["ADMIN_ID"]) 
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"] 
GITHUB_REPO = os.environ["GITHUB_REPO"] 
BASE_URL = os.environ["RENDER_EXTERNAL_URL"].rstrip("/") 
PORT = int(os.environ.get("PORT", "10000"))

DATA_FILE = "books.json"

CATEGORIES = { "1": ("Гуманітарні та соціально-економічні дисципліни", [ "Історія медицини та медсестринства", "Історія та культура України", "Українська мова за професійним спрямуванням", ]), "2": ("Загальноосвітні дисципліни", [ "Англійська мова", "Захист України", "Хімія", ]), "3": ("Клінічні дисципліни — лікувальна справа", [ "Акушерство і гінекологія", "Медична та соціальна реабілітація", "Неврологія", "Основи медсестринства. Догляд за хворими", "Педіатрія", "Психіатрія", ]), "4": ("Клінічні дисципліни — сестринська справа", [ "Акушерство і гінекологія", "Медична та соціальна реабілітація", "Медсестринство в геронтології та геріатрії", "Медсестринство в інфектології", "Медсестринство в неврології", "Медсестринство в педіатрії", "Основи медсестринства. Догляд за хворими", "Психіатрія", ]), "5": ("Природничо-наукові дисципліни — лікувальна справа", [ "Анатомія і фізіологія людини", "Медична хімія", "Мікробіологія з вірусологією та основами імунології", "Нутриціологія", "Основи психології міжособового спілкування", ]), "6": ("Природничо-наукові дисципліни — фармація", [ "Техніка лабораторних робіт", "Технологія ліків", "Фармацевтична хімія", ]), }
=========================
GITHUB
=========================
async def github_request(method, path, **kwargs): url = ( f"https://api.github.com/repos/" f"{GITHUB_REPO}/contents/{path}" )
headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

async with ClientSession() as session:
    async with session.request(
        method,
        url,
        headers=headers,
        **kwargs
    ) as response:
        data = await response.json(content_type=None)

        if response.status >= 400:
            raise RuntimeError(
                f"GitHub API error {response.status}: {data}"
            )

        return data
async def load_books(): try: result = await github_request("GET", DATA_FILE)
    content = base64.b64decode(
        result["content"]
    ).decode("utf-8")

    return json.loads(content), result["sha"]

except RuntimeError as error:
    if "404" in str(error):
        return [], None
    r
async def save_book(book): books, sha = await load_books() books.append(book)
content = base64.b64encode(
    json.dumps(
        books,
        ensure_ascii=False,
        indent=2
    ).encode("utf-8")
).decode("ascii")

body = {
    "message": "Update BMFK electronic library",
    "content": content,
}

if sha:
    body["sha"] = sha

await github_request(
    "PUT",
    DATA_FILE,
    json=body
)
=========================
КЛАВІАТУРИ
=========================
def category_keyboard(): keyboard = [ [ InlineKeyboardButton( name, callback_data=f"cat:{key}" ) ] for key, (name, _) in CATEGORIES.items() ]
keyboard.append([
    InlineKeyboardButton(
        "🏠 Головне меню",
        callback_data="home"
    )
])

return InlineKeyboardMarkup(keyboard)
def subject_keyboard(key): keyboard = [ [ InlineKeyboardButton( subject, callback_data=f"sub:{key}:{i}" ) ] for i, subject in enumerate(CATEGORIES[key][1]) ]
keyboard.append([
    InlineKeyboardButton(
        "⬅️ Назад",
        callback_data="categories"
    )
])

return InlineKeyboardMarkup(keyboard)
def admin_category_keyboard(): return InlineKeyboardMarkup([ [ InlineKeyboardButton( name, callback_data=f"admincat:{key}" ) ] for key, (name, _) in CATEGORIES.items() ])
def suggestion_category_keyboard(suggestion_id): return InlineKeyboardMarkup([ [ InlineKeyboardButton( name, callback_data=f"sugcat:{suggestion_id}:{key}" ) ] for key, (name, _) in CATEGORIES.items() ])
=========================
ГОЛОВНЕ МЕНЮ
=========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): context.user_data.clear()
keyboard = [
    [
        InlineKeyboardButton(
            "📚 Підручники",
            callback_data="categories"
        )
    ],
    [
        InlineKeyboardButton(
            "🔎 Пошук матеріалів",
            callback_data="search"
        )
    ],
    [
        InlineKeyboardButton(
            "📤 Запропонувати файл",
            callback_data="suggest"
        )
    ],
    [
        InlineKeyboardButton(
            "ℹ️ Допомога",
            callback_data="help"
        )
    ],
]

await update.effective_message.reply_text(
    "📚 ЕЛЕКТРОННА БІБЛІОТЕКА БМФК\n\n"
    "Оберіть потрібний розділ:",
    reply_markup=InlineKeyboardMarkup(keyboard),
)
=========================
ВІДПРАВЛЕННЯ ПІДРУЧНИКІВ
=========================
async def send_book(message, book): title = book.get("title", "Навчальний матеріал")
if book.get("file_id"):
    await message.reply_document(
        document=book["file_id"],
        caption=title
    )

elif book.get("url"):
    await message.reply_text(
        f"📖 {title}\n\n{book['url']}"
    )
async def show_subject_books(update, context, key, index): subject = CATEGORIES[key][1][index]
try:
    books, _ = await load_books()

except Exception as error:
    print(f"Load books error: {error}")

    await update.effective_message.reply_text(
        "Не вдалося завантажити каталог. Спробуйте пізніше."
    )
    return

matches = [
    book for book in books
    if book.get("category") == key
    and book.get("subject") == subject
]

if not matches:
    await update.effective_message.reply_text(
        f"📚 {subject}\n\nПідручники ще додаються."
    )
    return

await update.effective_message.reply_text(
    f"📚 {subject}"
)

for book in matches:
    try:
        await send_book(update.effective_message, book)

    except Exception as error:
        print(f"Send book error: {error}")

        await update.effective_message.reply_text(
            f"Не вдалося надіслати файл: "
            f"{book.get('title', 'Без назви')}"
        )
=========================
ОБРОБКА КНОПОК
=========================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer()
data = query.data
user_id = update.effective_user.id

if data == "home":
    await start(update, context)

elif data == "categories":
    await query.message.reply_text(
        "📚 Оберіть категорію:",
        reply_markup=category_keyboard()
    )

elif data.startswith("cat:"):
    key = data.split(":")[1]

    if key not in CATEGORIES:
        return

    await query.message.reply_text(
        CATEGORIES[key][0],
        reply_markup=subject_keyboard(key)
    )

elif data.startswith("sub:"):
    _, key, index = data.split(":")

    if key not in CATEGORIES:
        return

    index = int(index)

    if not 0 <= index < len(CATEGORIES[key][1]):
        return

    await show_subject_books(
        update,
        context,
        key,
        index
    )

elif data == "search":
    context.user_data["search_mode"] = True

    await query.message.reply_text(
        "🔎 Напишіть назву предмета або підручника для пошуку."
    )

elif data == "suggest":
    context.user_data.clear()
    context.user_data["awaiting_suggestion"] = True

    await query.message.reply_text(
        "📤 Надішліть PDF-файл або посилання на навчальний матеріал.\n\n"
        "Ваше повідомлення буде передане адміністратору "
        "для перевірки."
    )

elif data == "help":
    await query.message.reply_text(
        "ℹ️ Оберіть категорію, потім предмет, "
        "щоб отримати PDF або посилання.\n\n"
        "Для пошуку скористайтеся кнопкою "
        "«Пошук матеріалів».\n\n"
        "Щоб запропонувати новий матеріал, "
        "натисніть «Запропонувати файл»."
    )

elif data.startswith("admincat:"):
    if user_id != ADMIN_ID:
        return

    key = data.split(":")[1]

    if key not in CATEGORIES:
        return

    context.user_data["upload_category"] = key

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                subject,
                callback_data=f"adminsub:{i}"
            )
        ]
        for i, subject in enumerate(CATEGORIES[key][1])
    ])

    await query.message.reply_text(
        "Оберіть предмет:",
        reply_markup=keyboard
    )

elif data.startswith("adminsub:"):
    if user_id != ADMIN_ID:
        return

    index = int(data.split(":")[1])
    key = context.user_data.get("upload_category")

    if not key or key not in CATEGORIES:
        await query.message.reply_text(
            "Почніть додавання з /upload."
        )
        return

    if not 0 <= index < len(CATEGORIES[key][1]):
        return

    context.user_data["upload_subject"] = (
        CATEGORIES[key][1][index]
    )

    context.user_data["awaiting_pdf"] = True

    await query.message.reply_text(
        "Тепер надішліть PDF-документ як файл (📎 → Файл)."
    )

elif data.startswith("sugapprove:"):
    if user_id != ADMIN_ID:
        return

    suggestion_id = data.split(":")[1]

    pending = context.bot_data.get(
        "pending_suggestions", {}
    )

    if suggestion_id not in pending:
        await query.message.reply_text(
            "Ця пропозиція вже недоступна. "
            "Можливо, бот перезапускався."
        )
        return

    await query.message.reply_text(
        "Оберіть категорію для цього матеріалу:",
        reply_markup=suggestion_category_keyboard(
            suggestion_id
        )
    )

elif data.startswith("sugcat:"):
    if user_id != ADMIN_ID:
        return

    _, suggestion_id, key = data.split(":")

    pending = context.bot_data.get(
        "pending_suggestions", {}
    )

    if suggestion_id not in pending or key not in CATEGORIES:
        return

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                subject,
                callback_data=f"sugsub:{suggestion_id}:{i}"
            )
        ]
        for i, subject in enumerate(CATEGORIES[key][1])
    ])

    context.user_data["suggestion_category"] = key

    await query.message.reply_text(
        "Оберіть предмет:",
        reply_markup=keyboard
    )

elif data.startswith("sugsub:"):
    if user_id != ADMIN_ID:
        return

    _, suggestion_id, index = data.split(":")

    pending = context.bot_data.get(
        "pending_suggestions", {}
    )

    suggestion = pending.get(suggestion_id)
    key = context.user_data.get("suggestion_category")

    if not suggestion or not key or key not in CATEGORIES:
        await query.message.reply_text(
            "Пропозиція більше недоступна. Спробуйте ще раз."
        )
        return

    index = int(index)

    if not 0 <= index < len(CATEGORIES[key][1]):
        return

    subject = CATEGORIES[key][1][index]

    book = {
        "category": key,
        "subject": subject,
        "title": suggestion["title"],
    }

    if suggestion.get("file_id"):
        book["file_id"] = suggestion["file_id"]

    if suggestion.get("url"):
        book["url"] = suggestion["url"]

    try:
        await save_book(book)

        del pending[suggestion_id]

        context.user_data.pop(
            "suggestion_category",
            None
        )

        await query.message.reply_text(
            f"✅ Матеріал додано до бібліотеки!\n\n"
            f"Предмет: {subject}\n"
            f"Назва: {suggestion['title']}"
        )

        await context.bot.send_message(
            chat_id=suggestion["user_id"],
            text=(
                "✅ Ваш запропонований матеріал пройшов "
                "перевірку та доданий до електронної "
                "бібліотеки БМФК."
            )
        )

    except Exception as error:
        print(f"Suggestion save error: {error}")

        await query.message.reply_text(
            "Не вдалося зберегти матеріал. "
            "Перевірте налаштування GitHub."
        )

elif data.startswith("sugreject:"):
    if user_id != ADMIN_ID:
        return

    suggestion_id = data.split(":")[1]

    pending = context.bot_data.get(
        "pending_suggestions", {}
    )

    suggestion = pending.pop(suggestion_id, None)

    if not suggestion:
        await query.message.reply_text(
            "Ця пропозиція вже недоступна."
        )
        return

    await query.message.reply_text(
        "Пропозицію відхилено."
    )

    await context.bot.send_message(
        chat_id=suggestion["user_id"],
        text=(
            "Дякуємо за пропозицію! "
            "На жаль, матеріал не було додано до бібліотеки."
        )
    )
=========================
ЗАВАНТАЖЕННЯ ПІДРУЧНИКА АДМІНІСТРАТОРОМ
=========================
async def upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE): if update.effective_user.id != ADMIN_ID: await update.effective_message.reply_text( "Додавати підручники може лише адміністратор." ) return
context.user_data.clear()

await update.effective_message.reply_text(
    "Оберіть категорію для нового підручника:",
    reply_markup=admin_category_keyboard()
)
=========================
ПРОПОЗИЦІЇ ВІД СТУДЕНТІВ
=========================
async def send_suggestion_to_admin(update, context, suggestion): suggestion_id = uuid.uuid4().hex[:10]
if "pending_suggestions" not in context.bot_data:
    context.bot_data["pending_suggestions"] = {}

context.bot_data["pending_suggestions"][suggestion_id] = suggestion

keyboard = InlineKeyboardMarkup([
    [
        InlineKeyboardButton(
            "✅ Прийняти",
            callback_data=f"sugapprove:{suggestion_id}"
        ),
        InlineKeyboardButton(
            "❌ Відхилити",
            callback_data=f"sugreject:{suggestion_id}"
        )
    ]
])

if suggestion.get("file_id"):
    await context.bot.send_document(
        chat_id=ADMIN_ID,
        document=suggestion["file_id"],
        caption=(
            "📥 НОВА ПРОПОЗИЦІЯ ДО БІБЛІОТЕКИ\n\n"
            f"Назва: {suggestion['title']}\n"
            f"Від користувача: {suggestion['user_id']}"
        ),
        reply_markup=keyboard
    )

else:
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=(
            "📥 НОВА ПРОПОЗИЦІЯ ДО БІБЛІОТЕКИ\n\n"
            f"Назва: {suggestion['title']}\n"
            f"Посилання: {suggestion['url']}\n"
            f"Від користувача: {suggestion['user_id']}"
        ),
        reply_markup=keyboard
    )

await update.effective_message.reply_text(
    "✅ Дякуємо! Ваш матеріал передано адміністратору на перевірку."
)
=========================
ОБРОБКА ПОВІДОМЛЕНЬ
=========================
async def receive_document(update: Update, context: ContextTypes.DEFAULT_TYPE): message = update.effective_message user_id = update.effective_user.id
if context.user_data.get("awaiting_suggestion"):

    document = message.document

    if document:
        filename = document.file_name or "Підручник.pdf"

        if not filename.lower().endswith(".pdf"):
            await message.reply_text(
                "Будь ласка, надішліть PDF-файл."
            )
            return

        suggestion = {
            "title": filename,
            "file_id": document.file_id,
            "user_id": user_id,
        }

        try:
            await send_suggestion_to_admin(
                update,
                context,
                suggestion
            )
            context.user_data.clear()

        except Exception as error:
            print(f"Suggestion error: {error}")

            await message.reply_text(
                "Не вдалося передати файл. Спробуйте пізніше."
            )

        return

    if message.text:
        url = message.text.strip()
        parsed = urlsplit(url)

        if (
            parsed.scheme not in ("http", "https")
            or not parsed.netloc
            or any(char.isspace() for char in url)
        ):
            await message.reply_text(
                "Надішліть посилання, яке починається з "
                "https:// або http://, або PDF-файл."
            )
            return

        suggestion = {
            "title": parsed.netloc,
            "url": url,
            "user_id": user_id,
        }

        try:
            await send_suggestion_to_admin(
                update,
                context,
                suggestion
            )
            context.user_data.clear()

        except Exception as error:
            print(f"Suggestion error: {error}")

            await message.reply_text(
                "Не вдалося передати посилання. Спробуйте пізніше."
            )

        return

if context.user_data.get("awaiting_pdf"):

    if user_id != ADMIN_ID:
        return

    document = message.document

    if not document:
        await message.reply_text(
            "Будь ласка, надішліть PDF як документ."
        )
        return

    filename = document.file_name or ""

    if not filename.lower().endswith(".pdf"):
        await message.reply_text(
            "Потрібно надіслати саме PDF-файл."
        )
        return

    key = context.user_data.get("upload_category")
    subject = context.user_data.get("upload_subject")

    if not key or not subject:
        await message.reply_text(
            "Почніть додавання заново командою /upload."
        )
        return

    book = {
        "category": key,
        "subject": subject,
        "title": filename,
        "file_id": document.file_id,
    }

    try:
        await save_book(book)

        context.user_data.clear()

        await message.reply_text(
            f"✅ Додано до бібліотеки!\n"
            f"Предмет: {subject}\n"
            f"Файл: {filename}"
        )

    except Exception as error:
        print(f"Save error: {error}")

        await message.reply_text(
            "Не вдалося зберегти каталог. "
            "Перевірте налаштування GitHub."
        )

    return

if context.user_data.get("search_mode"):

    if not message.text:
        await message.reply_text(
            "Для пошуку напишіть назву предмета або підручника."
        )
        return

    search_query = message.text.lower().strip()
    context.user_data["search_mode"] = False

    if not search_query:
        await message.reply_text(
            "Введіть назву для пошуку."
        )
        return

    try:
        books, _ = await load_books()

        matches = [
            book for book in books
            if search_query in book.get("title", "").lower()
            or search_query in book.get("subject", "").lower()
        ]

        if not matches:
            await message.reply_text(
                "Нічого не знайдено. Спробуйте іншу назву."
            )

        else:
            await message.reply_text(
                f"🔎 Знайдено матеріалів: {len(matches)}"
            )

            for book in matches:
                await send_book(message, book)

    except Exception as error:
        print(f"Search error: {error}")

        await message.reply_text(
            "Пошук тимчасово недоступний."
        )
=========================
ДОПОМОГА
=========================
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.effective_message.reply_text( "/start — головне меню\n" "/upload — додати підручник (лише адміністратор)\n" "/cancel — скасувати поточну дію\n" "/help — допомога" )
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE): context.user_data.clear()
await update.effective_message.reply_text(
    "Дію скасовано. Щоб повернутися до бібліотеки, "
    "натисніть /start."
)
=========================
WEBHOOK
=========================
telegram_app = None
async def webhook(request): if request.match_info["token"] != TOKEN: raise web.HTTPNotFound()
try:
    data = await request.json()

    update = Update.de_json(
        data,
        telegram_app.bot
    )

    await telegram_app.process_update(update)

    return web.Response(text="OK")

except Exception as error:
    print(f"Webhook error: {error}")

    return web.Response(
        status=500,
        text="Error"
    )
=========================
ЗАПУСК БОТА
=========================
async def main(): global telegram_app
telegram_app = (
    Application.builder()
    .token(TOKEN)
    .build()
)

telegram_app.add_handler(
    CommandHandler("start", start)
)

telegram_app.add_handler(
    CommandHandler("upload", upload_command)
)

telegram_app.add_handler(
    CommandHandler("help", help_command)
)

telegram_app.add_handler(
    CommandHandler("cancel", cancel_command)
)

telegram_app.add_handler(
    CallbackQueryHandler(buttons)
)

telegram_app.add_handler(
    MessageHandler(
        filters.Document.ALL | (filters.TEXT & ~filters.COMMAND),
        receive_document
    )
)

await telegram_app.initialize()
await telegram_app.start()

server = web.Application()

server.router.add_post(
    "/{token}",
    webhook
)

runner = web.AppRunner(server)

await runner.setup()

site = web.TCPSite(
    runner,
    "0.0.0.0",
    PORT
)

await site.start()

await telegram_app.bot.set_webhook(
    f"{BASE_URL}/{TOKEN}"
)

print(f"Bot running on port {PORT}")

try:
    await asyncio.Event().wait()

finally:
    await runner.cleanup()
    await telegram_app.stop()
    await telegram_app.shutdown()
if name == "main": asyncio.run(main())
