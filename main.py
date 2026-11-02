import os
import json
import uuid
import base64
import asyncio

import aiohttp
from aiohttp import web

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)


# ==============================
# НАСТРОЙКИ
# ==============================

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_REPO = os.environ["GITHUB_REPO"]

PORT = int(os.environ.get("PORT", "10000"))

DATA_FILE = "books.json"

GITHUB_URL = (
    f"https://api.github.com/repos/"
    f"{GITHUB_REPO}/contents/{DATA_FILE}"
)

GITHUB_HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

SAVE_LOCK = asyncio.Lock()


# ==============================
# КАТЕГОРИИ И ПРЕДМЕТЫ
# ==============================

CATEGORIES = {
    "Гуманітарні та соціально-економічні дисципліни": [
        "Історія медицини та медсестринства",
        "Історія та культура України",
        "Українська мова за професійним спрямуванням",
    ],

    "Загальноосвітні дисципліни": [
        "Англійська мова",
        "Захист України",
        "Хімія",
    ],

    "Клінічні дисципліни — лікувальна справа": [
        "Акушерство і гінекологія",
        "Медична та соціальна реабілітація",
        "Неврологія",
        "Основи медсестринства. Догляд за хворими",
        "Педіатрія",
        "Психіатрія",
    ],

    "Клінічні дисципліни — сестринська справа": [
        "Акушерство і гінекологія",
        "Медична та соціальна реабілітація",
        "Медсестринство в геронтології та геріатрії",
        "Медсестринство в інфектології",
        "Медсестринство в неврології",
        "Медсестринство в педіатрії",
        "Основи медсестринства. Догляд за хворими",
        "Психіатрія",
    ],

    "Природничо-наукові дисципліни — лікувальна справа": [
        "Анатомія і фізіологія людини",
        "Медична хімія",
        "Мікробіологія з вірусологією та основами імунології",
        "Нутриціологія",
        "Основи психології міжособового спілкування",
    ],

    "Природничо-наукові дисципліни — фармація": [
        "Техніка лабораторних робіт",
        "Технологія ліків",
        "Фармацевтична хімія",
    ],
}


# ==============================
# GITHUB: ЗАГРУЗКА И СОХРАНЕНИЕ
# ==============================

async def load_books():
    async with aiohttp.ClientSession() as session:
        async with session.get(
            GITHUB_URL,
            headers=GITHUB_HEADERS,
        ) as response:

            if response.status == 404:
                return []

            if response.status != 200:
                error = await response.text()
                raise Exception(error)

            data = await response.json()

            content = base64.b64decode(
                data["content"]
            ).decode("utf-8")

            return json.loads(content)


async def save_books(books):
    async with SAVE_LOCK:
        async with aiohttp.ClientSession() as session:

            sha = None

            async with session.get(
                GITHUB_URL,
                headers=GITHUB_HEADERS,
            ) as response:

                if response.status == 200:
                    data = await response.json()
                    sha = data["sha"]

                elif response.status != 404:
                    error = await response.text()
                    raise Exception(error)

            content = json.dumps(
                books,
                ensure_ascii=False,
                indent=4,
            )

            encoded = base64.b64encode(
                content.encode("utf-8")
            ).decode("utf-8")

            payload = {
                "message": "Update textbook library",
                "content": encoded,
            }

            if sha:
                payload["sha"] = sha

            async with session.put(
                GITHUB_URL,
                headers=GITHUB_HEADERS,
                json=payload,
            ) as response:

                if response.status not in (200, 201):
                    error = await response.text()
                    raise Exception(error)


# ==============================
# КЛАВИАТУРЫ
# ==============================

def main_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📚 Підручники",
                callback_data="catalog",
            )
        ],
        [
            InlineKeyboardButton(
                "🔎 Пошук матеріалів",
                callback_data="search",
            )
        ],
        [
            InlineKeyboardButton(
                "📤 Запропонувати файл",
                callback_data="suggest",
            )
        ],
        [
            InlineKeyboardButton(
                "ℹ️ Допомога",
                callback_data="help",
            )
        ],
    ])


def category_keyboard(prefix):
    keyboard = []

    for index, category in enumerate(CATEGORIES):
        keyboard.append([
            InlineKeyboardButton(
                category,
                callback_data=f"{prefix}:{index}",
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "⬅️ Головне меню",
            callback_data="back",
        )
    ])

    return InlineKeyboardMarkup(keyboard)


def subject_keyboard(category_index, prefix):
    category = list(CATEGORIES.keys())[category_index]

    keyboard = []

    for index, subject in enumerate(CATEGORIES[category]):
        keyboard.append([
            InlineKeyboardButton(
                subject,
                callback_data=f"{prefix}:{category_index}:{index}",
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "⬅️ До категорій",
            callback_data="catalog",
        )
    ])

    return InlineKeyboardMarkup(keyboard)


# ==============================
# СТАРТ
# ==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    await update.message.reply_text(
        "Вітаємо у спільній бібліотеці підручників "
        "Бериславського медичного фахового коледжу! 📚\n\n"
        "Тут можна переглядати навчальні матеріали, "
        "шукати підручники та пропонувати власні файли.\n\n"
        "Оберіть потрібний розділ:",
        reply_markup=main_menu(),
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    await update.message.reply_text(
        "Дію скасовано.",
        reply_markup=main_menu(),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 Допомога\n\n"
        "• Підручники — перегляд матеріалів за категоріями.\n"
        "• Пошук — пошук за назвою або предметом.\n"
        "• Запропонувати файл — надсилання PDF або посилання.\n\n"
        "Запропоновані матеріали перевіряє адміністратор."
    )


# ==============================
# КАТАЛОГ
# ==============================

async def show_catalog(query):
    await query.answer()

    await query.message.reply_text(
        "Оберіть категорію:",
        reply_markup=category_keyboard("cat"),
    )


async def show_subjects(query, category_index):
    await query.answer()

    await query.message.reply_text(
        "Оберіть навчальну дисципліну:",
        reply_markup=subject_keyboard(category_index, "sub"),
    )


async def show_books(query, category_index, subject_index):
    await query.answer()

    category = list(CATEGORIES.keys())[category_index]
    subject = CATEGORIES[category][subject_index]

    try:
        books = await load_books()
    except Exception:
        await query.message.reply_text(
            "Не вдалося завантажити бібліотеку. Спробуйте пізніше."
        )
        return

    found = [
        book for book in books
        if book.get("category") == category
        and book.get("subject") == subject
    ]

    if not found:
        await query.message.reply_text(
            "У цьому розділі поки немає матеріалів."
        )
        return

    keyboard = []

    for book in found:
        keyboard.append([
            InlineKeyboardButton(
                book.get("title", "Підручник"),
                callback_data=f"book:{book['id']}",
            )
        ])

    await query.message.reply_text(
        f"📚 {subject}\n\nОберіть матеріал:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def send_book(query, book_id, context):
    await query.answer()

    try:
        books = await load_books()
    except Exception:
        await query.message.reply_text(
            "Не вдалося завантажити матеріал."
        )
        return

    book = next(
        (item for item in books if item.get("id") == book_id),
        None,
    )

    if not book:
        await query.message.reply_text(
            "Матеріал не знайдено."
        )
        return

    title = book.get("title", "Навчальний матеріал")

    if book.get("file_id"):
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=book["file_id"],
            caption=f"📚 {title}",
        )

    elif book.get("url"):
        await query.message.reply_text(
            f"📚 {title}\n\n{book['url']}"
        )

    else:
        await query.message.reply_text(
            "Файл або посилання не знайдено."
        )


# ==============================
# ПОИСК
# ==============================

async def start_search(query, context):
    await query.answer()

    context.user_data.clear()
    context.user_data["state"] = "search"

    await query.message.reply_text(
        "Введіть назву підручника, предмета або ключове слово."
    )


async def search_books(update, context):
    search_text = update.message.text.lower().strip()

    try:
        books = await load_books()
    except Exception:
        await update.message.reply_text(
            "Не вдалося виконати пошук. Спробуйте пізніше."
        )
        context.user_data.clear()
        return

    found = []

    for book in books:
        searchable = " ".join([
            book.get("title", ""),
            book.get("category", ""),
            book.get("subject", ""),
        ]).lower()

        if search_text in searchable:
            found.append(book)

    context.user_data.clear()

    if not found:
        await update.message.reply_text(
            "За вашим запитом нічого не знайдено.",
            reply_markup=main_menu(),
        )
        return

    keyboard = []

    for book in found[:30]:
        keyboard.append([
            InlineKeyboardButton(
                book.get("title", "Матеріал"),
                callback_data=f"book:{book['id']}",
            )
        ])

    await update.message.reply_text(
        f"Знайдено матеріалів: {len(found)}.\nОберіть потрібний:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ==============================
# ПРЕДЛОЖЕНИЕ МАТЕРИАЛОВ
# ==============================

def valid_url(text):
    return (
        text.startswith("https://")
        or text.startswith("http://")
    )


async def start_suggestion(query, context):
    await query.answer()

    context.user_data.clear()
    context.user_data["state"] = "suggest"

    await query.message.reply_text(
        "📤 Надішліть PDF-файл або посилання на навчальний матеріал.\n\n"
        "Після перевірки адміністратор зможе додати його до бібліотеки."
    )


async def handle_suggestion(update, context):
    message = update.message

    if message.document:
        document = message.document
        filename = document.file_name or "Навчальний матеріал"

        if (
            document.mime_type != "application/pdf"
            and not filename.lower().endswith(".pdf")
        ):
            await message.reply_text(
                "Будь ласка, надсилайте файли у форматі PDF."
            )
            return

        suggestion = {
            "id": str(uuid.uuid4()),
            "title": filename,
            "file_id": document.file_id,
            "url": None,
            "user_id": message.from_user.id,
            "username": message.from_user.username or "немає",
        }

    elif message.text and valid_url(message.text.strip()):
        suggestion = {
            "id": str(uuid.uuid4()),
            "title": message.text.strip(),
            "file_id": None,
            "url": message.text.strip(),
            "user_id": message.from_user.id,
            "username": message.from_user.username or "немає",
        }

    else:
        await message.reply_text(
            "Надішліть PDF-файл або коректне посилання."
        )
        return

    context.user_data.clear()

    pending = context.bot_data.setdefault("pending", {})
    pending[suggestion["id"]] = suggestion

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ Додати",
                callback_data=f"approve:{suggestion['id']}",
            ),
            InlineKeyboardButton(
                "❌ Відхилити",
                callback_data=f"reject:{suggestion['id']}",
            ),
        ]
    ])

    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                "📥 Нова пропозиція до бібліотеки!\n\n"
                f"Назва: {suggestion['title']}\n"
                f"Користувач: @{suggestion['username']}\n"
                f"ID користувача: {suggestion['user_id']}\n\n"
                "Перевірте матеріал:"
            ),
            reply_markup=keyboard,
        )

        if suggestion["file_id"]:
            await context.bot.send_document(
                chat_id=ADMIN_ID,
                document=suggestion["file_id"],
            )

        await message.reply_text(
            "Дякуємо! Ваш матеріал надіслано адміністратору на перевірку. 📚"
        )

    except Exception:
        pending.pop(suggestion["id"], None)

        await message.reply_text(
            "Не вдалося передати матеріал адміністратору."
        )


# ==============================
# ПРЯМАЯ ЗАГРУЗКА АДМИНИСТРАТОРОМ
# ==============================

async def upload_command(update, context):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(
            "Ця команда доступна лише адміністратору."
        )
        return

    context.user_data.clear()
    context.user_data["state"] = "direct_category"

    await update.message.reply_text(
        "Оберіть категорію для нового підручника:",
        reply_markup=category_keyboard("dc"),
    )


async def save_admin_document(update, context):
    message = update.message

    if message.from_user.id != ADMIN_ID:
        await message.reply_text(
            "Додавати матеріали безпосередньо може лише адміністратор."
        )
        return

    document = message.document
    filename = document.file_name or "Навчальний матеріал"

    if (
        document.mime_type != "application/pdf"
        and not filename.lower().endswith(".pdf")
    ):
        await message.reply_text(
            "Будь ласка, надішліть PDF-файл."
        )
        return

    book = {
        "id": str(uuid.uuid4()),
        "title": filename,
        "category": context.user_data["category"],
        "subject": context.user_data["subject"],
        "file_id": document.file_id,
        "url": None,
    }

    try:
        books = await load_books()
        books.append(book)
        await save_books(books)

        context.user_data.clear()

        await message.reply_text(
            "✅ Підручник успішно додано до бібліотеки!",
            reply_markup=main_menu(),
        )

    except Exception:
        await message.reply_text(
            "Не вдалося зберегти підручник. Перевірте налаштування GitHub."
        )


# ==============================
# ПОДТВЕРЖДЕНИЕ МАТЕРИАЛОВ
# ==============================

async def approve_suggestion(query, context, suggestion_id):
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    pending = context.bot_data.setdefault("pending", {})
    suggestion = pending.get(suggestion_id)

    if not suggestion:
        await query.message.reply_text(
            "Пропозицію не знайдено або її вже оброблено."
        )
        return

    context.user_data.clear()
    context.user_data["state"] = "approve_category"
    context.user_data["pending_id"] = suggestion_id

    await query.message.reply_text(
        f"Оберіть категорію для матеріалу:\n\n{suggestion['title']}",
        reply_markup=category_keyboard("ac"),
    )


async def reject_suggestion(query, context, suggestion_id):
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    pending = context.bot_data.setdefault("pending", {})
    suggestion = pending.pop(suggestion_id, None)

    if not suggestion:
        await query.message.reply_text(
            "Цю пропозицію вже оброблено."
        )
        return

    await query.message.reply_text(
        "Пропозицію відхилено."
    )

    try:
        await context.bot.send_message(
            chat_id=suggestion["user_id"],
            text="На жаль, ваш матеріал не було додано до бібліотеки."
        )
    except Exception:
        pass


async def finish_approval(query, context, category_index, subject_index):
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    category = list(CATEGORIES.keys())[category_index]
    subject = CATEGORIES[category][subject_index]

    suggestion_id = context.user_data.get("pending_id")

    pending = context.bot_data.setdefault("pending", {})
    suggestion = pending.get(suggestion_id)

    if not suggestion:
        context.user_data.clear()

        await query.message.reply_text(
            "Пропозицію не знайдено. Можливо, її вже оброблено."
        )
        return

    book = {
        "id": str(uuid.uuid4()),
        "title": suggestion["title"],
        "category": category,
        "subject": subject,
        "file_id": suggestion["file_id"],
        "url": suggestion["url"],
    }

    try:
        books = await load_books()
        books.append(book)
        await save_books(books)

        pending.pop(suggestion_id, None)
        context.user_data.clear()

        await query.message.reply_text(
            "✅ Матеріал успішно додано до бібліотеки!"
        )

        try:
            await context.bot.send_message(
                chat_id=suggestion["user_id"],
                text="✅ Ваш матеріал перевірено та додано до бібліотеки. Дякуємо!"
            )
        except Exception:
            pass

    except Exception:
        await query.message.reply_text(
            "Не вдалося зберегти матеріал. Перевірте GitHub."
        )


# ==============================
# ОБРАБОТКА КНОПОК
# ==============================

async def button_handler(update, context):
    query = update.callback_query
    data = query.data

    if data == "catalog":
        context.user_data.clear()
        await show_catalog(query)
        return

    if data == "search":
        await start_search(query, context)
        return

    if data == "suggest":
        await start_suggestion(query, context)
        return

    if data == "help":
        await query.answer()
        await query.message.reply_text(
            "📚 Бібліотека навчальних матеріалів коледжу.\n\n"
            "Переглядайте підручники, шукайте матеріали "
            "або пропонуйте власні PDF-файли та посилання."
        )
        return

    if data == "back":
        context.user_data.clear()
        await query.answer()
        await query.message.reply_text(
            "Головне меню:",
            reply_markup=main_menu(),
        )
        return

    if data.startswith("cat:"):
        category_index = int(data.split(":")[1])
        await show_subjects(query, category_index)
        return

    if data.startswith("sub:"):
        _, category_index, subject_index = data.split(":")
        await show_books(
            query,
            int(category_index),
            int(subject_index),
        )
        return

    if data.startswith("book:"):
        book_id = data.split(":", 1)[1]
        await send_book(query, book_id, context)
        return

    if data.startswith("dc:"):
        await query.answer()

        if query.from_user.id != ADMIN_ID:
            return

        category_index = int(data.split(":")[1])

        context.user_data["category"] = list(CATEGORIES.keys())[category_index]
        context.user_data["state"] = "direct_subject"

        await query.message.reply_text(
            "Оберіть предмет:",
            reply_markup=subject_keyboard(category_index, "ds"),
        )
        return

    if data.startswith("ds:"):
        await query.answer()

        if query.from_user.id != ADMIN_ID:
            return

        _, category_index, subject_index = data.split(":")

        category_index = int(category_index)
        subject_index = int(subject_index)

        category = list(CATEGORIES.keys())[category_index]
        subject = CATEGORIES[category][subject_index]

        context.user_data["category"] = category
        context.user_data["subject"] = subject
        context.user_data["state"] = "direct_document"

        await query.message.reply_text(
            f"Категорія: {category}\n"
            f"Предмет: {subject}\n\n"
            "Тепер надішліть PDF-файл."
        )
        return

    if data.startswith("approve:"):
        suggestion_id = data.split(":", 1)[1]
        await approve_suggestion(query, context, suggestion_id)
        return

    if data.startswith("reject:"):
        suggestion_id = data.split(":", 1)[1]
        await reject_suggestion(query, context, suggestion_id)
        return

    if data.startswith("ac:"):
        await query.answer()

        if query.from_user.id != ADMIN_ID:
            return

        category_index = int(data.split(":")[1])

        context.user_data["category"] = list(CATEGORIES.keys())[category_index]
        context.user_data["state"] = "approve_subject"

        await query.message.reply_text(
            "Оберіть предмет:",
            reply_markup=subject_keyboard(category_index, "as"),
        )
        return

    if data.startswith("as:"):
        _, category_index, subject_index = data.split(":")

        await finish_approval(
            query,
            context,
            int(category_index),
            int(subject_index),
        )
        return

    await query.answer()


# ==============================
# ОБРАБОТКА СООБЩЕНИЙ
# ==============================

async def text_handler(update, context):
    state = context.user_data.get("state")

    if state == "search":
        await search_books(update, context)
        return

    if state == "suggest":
        await handle_suggestion(update, context)
        return

    await update.message.reply_text(
        "Оберіть потрібний розділ у меню:",
        reply_markup=main_menu(),
    )


async def document_handler(update, context):
    state = context.user_data.get("state")

    if state == "suggest":
        await handle_suggestion(update, context)
        return

    if state == "direct_document":
        await save_admin_document(update, context)
        return

    await update.message.reply_text(
        "Щоб запропонувати матеріал, спочатку оберіть "
        "«Запропонувати файл» у головному меню."
    )


# ==============================
# ВЕБ-СЕРВЕР ДЛЯ RENDER
# ==============================

async def health_check(request):
    return web.Response(text="Bot is running!")


async def start_web_server():
    app = web.Application()

    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        PORT,
    )

    await site.start()

    return runner


# ==============================
# ЗАПУСК
# ==============================

async def main():
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("upload", upload_command))

    application.add_handler(
        CallbackQueryHandler(button_handler)
    )

    application.add_handler(
        MessageHandler(
            filters.Document.ALL,
            document_handler,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_handler,
        )
    )

    runner = await start_web_server()

    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    print("BOT STARTED SUCCESSFULLY")

    try:
        await asyncio.Event().wait()

    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
