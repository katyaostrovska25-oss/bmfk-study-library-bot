import os
import json
import base64
import asyncio
import uuid
from urllib.parse import urlparse

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


# =========================
# НАСТРОЙКИ
# =========================

TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_REPO = os.environ["GITHUB_REPO"]

PORT = int(os.environ.get("PORT", "10000"))
DATA_FILE = "books.json"

GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DATA_FILE}"

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

SAVE_LOCK = asyncio.Lock()


# =========================
# КАТЕГОРИИ И ПРЕДМЕТЫ
# =========================

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


# =========================
# РАБОТА С БИБЛИОТЕКОЙ
# =========================

async def load_books():
    async with aiohttp.ClientSession() as session:
        async with session.get(
            GITHUB_API,
            headers=HEADERS,
        ) as response:

            if response.status == 404:
                return []

            if response.status != 200:
                error = await response.text()
                raise Exception(f"GitHub error: {error}")

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
                GITHUB_API,
                headers=HEADERS,
            ) as response:

                if response.status == 200:
                    data = await response.json()
                    sha = data["sha"]

                elif response.status != 404:
                    error = await response.text()
                    raise Exception(f"GitHub error: {error}")

            content = json.dumps(
                books,
                ensure_ascii=False,
                indent=4,
            )

            encoded_content = base64.b64encode(
                content.encode("utf-8")
            ).decode("utf-8")

            payload = {
                "message": "Update textbook library",
                "content": encoded_content,
            }

            if sha:
                payload["sha"] = sha

            async with session.put(
                GITHUB_API,
                headers=HEADERS,
                json=payload,
            ) as response:

                if response.status not in (200, 201):
                    error = await response.text()
                    raise Exception(f"GitHub save error: {error}")


# =========================
# КЛАВИАТУРЫ
# =========================

def main_menu():
    keyboard = [
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
    ]

    return InlineKeyboardMarkup(keyboard)


def categories_keyboard(prefix):
    keyboard = []

    for index, category in enumerate(CATEGORIES.keys()):
        keyboard.append([
            InlineKeyboardButton(
                category,
                callback_data=f"{prefix}:{index}",
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="back_menu",
        )
    ])

    return InlineKeyboardMarkup(keyboard)


def subjects_keyboard(category_index, prefix):
    category = list(CATEGORIES.keys())[category_index]
    subjects = CATEGORIES[category]

    keyboard = []

    for index, subject in enumerate(subjects):
        keyboard.append([
            InlineKeyboardButton(
                subject,
                callback_data=f"{prefix}:{category_index}:{index}",
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="catalog",
        )
    ])

    return InlineKeyboardMarkup(keyboard)


# =========================
# СТАРТ И ПОМОЩЬ
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    await update.message.reply_text(
        "Вітаємо у спільній бібліотеці підручників Бериславського медичного фахового коледжу! 📚\n\n"
        "Тут можна переглядати навчальні матеріали, шукати підручники "
        "та пропонувати власні файли для бібліотеки.\n\n"
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
        "📚 Як користуватися бібліотекою:\n\n"
        "• «Підручники» — перегляд матеріалів за категоріями та предметами.\n"
        "• «Пошук матеріалів» — пошук за назвою підручника або предметом.\n"
        "• «Запропонувати файл» — надсилання PDF-файлу або посилання.\n\n"
        "Запропоновані матеріали спочатку перевіряються адміністратором."
    )


# =========================
# ПРОСМОТР КАТАЛОГА
# =========================

async def show_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "Оберіть категорію:",
        reply_markup=categories_keyboard("browsecat"),
    )


async def show_subjects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    parts = query.data.split(":")
    category_index = int(parts[1])

    await query.edit_message_text(
        "Оберіть навчальну дисципліну:",
        reply_markup=subjects_keyboard(category_index, "browsesub"),
    )


async def show_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    parts = query.data.split(":")
    category_index = int(parts[1])
    subject_index = int(parts[2])

    category = list(CATEGORIES.keys())[category_index]
    subject = CATEGORIES[category][subject_index]

    try:
        books = await load_books()
    except Exception:
        await query.edit_message_text(
            "Не вдалося завантажити бібліотеку. Спробуйте пізніше."
        )
        return

    found = [
        book for book in books
        if book.get("category") == category
        and book.get("subject") == subject
    ]

    if not found:
        await query.edit_message_text(
            "У цьому розділі поки немає матеріалів.\n\n"
            "Ви можете запропонувати підручник через головне меню.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "⬅️ До каталогу",
                        callback_data="catalog",
                    )
                ]
            ]),
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

    keyboard.append([
        InlineKeyboardButton(
            "⬅️ До каталогу",
            callback_data="catalog",
        )
    ])

    await query.edit_message_text(
        f"📚 {subject}\n\nОберіть матеріал:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def send_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    book_id = query.data.split(":")[1]

    try:
        books = await load_books()
    except Exception:
        await query.message.reply_text(
            "Не вдалося завантажити матеріал. Спробуйте пізніше."
        )
        return

    book = next(
        (item for item in books if item.get("id") == book_id),
        None,
    )

    if not book:
        await query.message.reply_text(
            "Цей матеріал більше не знайдено в бібліотеці."
        )
        return

    title = book.get("title", "Навчальний матеріал")

    if book.get("file_id"):
        await query.message.reply_document(
            document=book["file_id"],
            caption=f"📚 {title}",
        )

    elif book.get("url"):
        await query.message.reply_text(
            f"📚 {title}\n\n{book['url']}"
        )

    else:
        await query.message.reply_text(
            "Для цього матеріалу файл або посилання не знайдено."
        )


# =========================
# ПОИСК
# =========================

async def search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["state"] = "search"

    await query.message.reply_text(
        "Введіть назву підручника, предмета або ключове слово для пошуку."
    )


async def search_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower().strip()

    try:
        books = await load_books()
    except Exception:
        await update.message.reply_text(
            "Не вдалося виконати пошук. Спробуйте пізніше."
        )
        return

    found = []

    for book in books:
        searchable = " ".join([
            book.get("title", ""),
            book.get("category", ""),
            book.get("subject", ""),
        ]).lower()

        if text in searchable:
            found.append(book)

    context.user_data.clear()

    if not found:
        await update.message.reply_text(
            "За вашим запитом нічого не знайдено."
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


# =========================
# ПРЕДЛОЖЕНИЕ МАТЕРИАЛОВ
# =========================

async def suggest_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data.clear()
    context.user_data["state"] = "suggest"

    await query.message.reply_text(
        "📤 Надішліть PDF-файл або посилання на навчальний матеріал.\n\n"
        "Після перевірки адміністратор зможе додати його до бібліотеки."
    )


def valid_url(text):
    try:
        parsed = urlparse(text.strip())
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


async def handle_suggestion(update: Update, context: ContextTypes.DEFAULT_TYPE): message = update.message
if message.document:
    document = message.document

    if document.mime_type != "application/pdf" and not (document.file_name or "").lower().endswith(".pdf"):
        await message.reply_text(
            "Будь ласка, надсилайте файли у форматі PDF."
        )
        return

    suggestion = {
        "id": str(uuid.uuid4()),
        "title": document.file_name or "Навчальний матеріал",
        "file_id": document.file_id,
        "url": None,
        "user_id": message.from_user.id,
        "username": message.from_user.username or "немає",
    }

elif message.text and valid_url(message.text):
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
        "Надішліть PDF-файл або коректне посилання, яке починається з http:// або https://."
    )
    return

context.user_data.clear()

pending = context.bot_data.setdefault("pending", {})
pending[suggestion["id"]] = suggestion

keyboard = InlineKeyboardMarkup([
    [
        InlineKeyboardButton(
            "✅ Додати до бібліотеки",
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
            "Перевірте матеріал та оберіть дію:"
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
        "Не вдалося передати матеріал адміністратору. Спробуйте пізніше."
    )


# =========================
# ДОБАВЛЕНИЕ МАТЕРИАЛА АДМИНИСТРАТОРОМ
# =========================

async def upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(
            "Ця команда доступна лише адміністратору."
        )
        return

    context.user_data.clear()
    context.user_data["state"] = "direct_category"

    await update.message.reply_text(
        "Оберіть категорію для нового підручника:",
        reply_markup=categories_keyboard("dcat"),
    )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    state = context.user_data.get("state")

    if state == "suggest":
        await handle_suggestion(update, context)
        return

    if state == "direct_document":
        if message.from_user.id != ADMIN_ID:
            await message.reply_text(
                "Додавати матеріали безпосередньо може лише адміністратор."
            )
            return

        document = message.document

        if document.mime_type != "application/pdf" and not document.file_name.lower().endswith(".pdf"):
            await message.reply_text(
                "Будь ласка, надішліть файл у форматі PDF."
            )
            return

        book = {
            "id": str(uuid.uuid4()),
            "title": document.file_name or "Навчальний матеріал",
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

        return

    await message.reply_text(
        "Щоб запропонувати матеріал, спочатку оберіть «Запропонувати файл»."
    )


# =========================
# ОБРАБОТКА КНОПОК
# =========================

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == "catalog":
        context.user_data.clear()
        await show_catalog(update, context)
        return

    if data == "search":
        await search_start(update, context)
        return

    if data == "suggest":
        await suggest_start(update, context)
        return

    if data == "help":
        await query.answer()
        await query.message.reply_text(
            "📚 Бібліотека навчальних матеріалів коледжу.\n\n"
            "Ви можете переглядати підручники, шукати матеріали "
            "та пропонувати власні PDF-файли або посилання."
        )
        return

    if data == "back_menu":
        context.user_data.clear()
        await query.answer()
        await query.message.reply_text(
            "Головне меню:",
            reply_markup=main_menu(),
        )
        return

    if data.startswith("browsecat:"):
        await show_subjects(update, context)
        return

    if data.startswith("browsesub:"):
        await show_books(update, context)
        return

    if data.startswith("book:"):
        await send_book(update, context)
        return

    # Пряма загрузка администратором

    if data.startswith("dcat:"):
        await query.answer()

        if query.from_user.id != ADMIN_ID:
            return

        category_index = int(data.split(":")[1])
        category = list(CATEGORIES.keys())[category_index]

        context.user_data["category"] = category
        context.user_data["state"] = "direct_subject"

        await query.message.reply_text(
            "Оберіть предмет:",
            reply_markup=subjects_keyboard(category_index, "dsub"),
        )
        return

    if data.startswith("dsub:"):
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
            "Тепер надішліть PDF-файл підручника."
        )
        return

    # Подтверждение предложенного материала

    if data.startswith("approve:"):
        await query.answer()

        if query.from_user.id != ADMIN_ID:
            return

        suggestion_id = data.split(":")[1]
        pending = context.bot_data.get("pending", {})
        suggestion = pending.get(suggestion_id)

        if not suggestion:
            await query.message.reply_text(
                "Цю пропозицію вже оброблено або вона недоступна."
            )
            return

        context.user_data.clear()
        context.user_data["state"] = "approve_category"
        context.user_data["pending_id"] = suggestion_id

        await query.message.reply_text(
            f"Оберіть категорію для матеріалу:\n\n{suggestion['title']}",
            reply_markup=categories_keyboard("apcat"),
        )
        return

    if data.startswith("apcat:"):
        await query.answer()

        if query.from_user.id != ADMIN_ID:
            return

        category_index = int(data.split(":")[1])
        category = list(CATEGORIES.keys())[category_index]

        context.user_data["category"] = category
        context.user_data["state"] = "approve_subject"

        await query.message.reply_text(
            "Оберіть предмет:",
            reply_markup=subjects_keyboard(category_index, "apsub"),
        )
        return

    if data.startswith("apsub:"):
        await query.answer()

        if query.from_user.id != ADMIN_ID:
            return

        _, category_index, subject_index = data.split(":")
        category_index = int(category_index)
        subject_index = int(subject_index)

        category = list(CATEGORIES.keys())[category_index]
        subject = CATEGORIES[category][subject_index]

        suggestion_id = context.user_data.get("pending_id")
        pending = context.bot_data.get("pending", {})
        suggestion = pending.get(suggestion_id)

        if not suggestion:
            await query.message.reply_text(
                "Пропозицію не знайдено. Можливо, її вже оброблено."
            )
            context.user_data.clear()
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

            await context.bot.send_message(
                chat_id=suggestion["user_id"],
                text="✅ Ваш матеріал перевірено та додано до бібліотеки. Дякуємо за допомогу!"
            )

        except Exception:
            await query.message.reply_text(
                "Не вдалося зберегти матеріал. Перевірте налаштування GitHub."
            )

        return

    if data.startswith("reject:"):
        await query.answer()

        if query.from_user.id != ADMIN_ID:
            return

        suggestion_id = data.split(":")[1]
        pending = context.bot_data.get("pending", {})
        suggestion = pending.pop(suggestion_id, None)

        if suggestion:
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
        else:
            await query.message.reply_text(
                "Цю пропозицію вже оброблено."
            )

        return

    await query.answer()


# =========================
# ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ
# =========================

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
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


# =========================
# ВЕБ-СЕРВЕР ДЛЯ RENDER
# =========================

async def health(request):
    return web.Response(text="Bot is running!")


async def run_web_server():
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        PORT,
    )

    await site.start()

    return runner


# =========================
# ЗАПУСК БОТА
# =========================

async def main():
    application = (
        Application.builder()
        .token(TOKEN)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CommandHandler("upload", upload_command))
    application.add_handler(CommandHandler("help", help_command))

    application.add_handler(CallbackQueryHandler(handle_callback))

    application.add_handler(
        MessageHandler(
            filters.Document.ALL,
            handle_document,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text,
        )
    )

    runner = await run_web_server()

    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    print("Bot started successfully!")

    try:
        await asyncio.Event().wait()

    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
