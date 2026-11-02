import os
import json
import base64
import logging
import asyncio
from aiohttp import web
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# Налаштування логування
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Отримання змінних середовища
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID_STR = os.getenv("ADMIN_ID")
ADMIN_ID = int(ADMIN_ID_STR) if ADMIN_ID_STR and ADMIN_ID_STR.isdigit() else 0

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")  # Наприклад: "username/bmfk-study-library-bot"
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")

# Обов'язкова структура категорій та дисциплін
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


# --- РОБОТА З GITHUB API ДЛЯ ЗБЕРЕЖЕННЯ БАЗИ ДАНИХ (books.json) ---

async def load_books_from_github() -> list:
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return []
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/books.json"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    import aiohttp
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    file_content = base64.b64decode(data["content"]).decode("utf-8")
                    return json.loads(file_content)
        except Exception as e:
            logger.error(f"Помилка завантаження books.json з GitHub: {e}")
    return []


async def save_books_to_github(books: list, commit_message: str):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return False
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/books.json"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    import aiohttp
    async with aiohttp.ClientSession() as session:
        try:
            sha = None
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    file_data = await resp.json()
                    sha = file_data.get("sha")

            updated_content = json.dumps(books, ensure_ascii=False, indent=4)
            encoded_content = base64.b64encode(updated_content.encode("utf-8")).decode("utf-8")

            payload = {
                "message": commit_message,
                "content": encoded_content,
                "branch": GITHUB_BRANCH,
            }
            if sha:
                payload["sha"] = sha

            async with session.put(url, headers=headers, json=payload) as put_resp:
                if put_resp.status in [200, 201]:
                    return True
                else:
                    logger.error(f"Помилка збереження на GitHub: {await put_resp.text()}")
        except Exception as e:
            logger.error(f"Виняток при збереженні на GitHub: {e}")
    return False


# --- КЛАВІАТУРИ ---

def get_main_menu(user_id: int):
    keyboard = [
        [KeyboardButton("📚 Підручники"), KeyboardButton("🔎 Пошук матеріалів")],
        [KeyboardButton("📤 Запропонувати файл"), KeyboardButton("ℹ️ Допомога")],
    ]
    if user_id == ADMIN_ID:
        keyboard.append([KeyboardButton("⚙️ Адмін-панель")])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# --- ОБРОБНИКИ КОМАНД ТА ПОВІДОМЛЕНЬ ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"Вітаю, {user.first_name}! 👋\n\n"
        "Це офіційний бот електронної бібліотеки **Бериславського медичного фахового колледжу**.\n"
        "Тут ви можете шукати, читати та завантажувати навчальні матеріали й підручники.\n\n"
        "Оберіть потрібний розділ у меню нижче:"
    )
    await update.message.reply_text(text, reply_markup=get_main_menu(user.id), parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "ℹ️ **Довідка користувача бібліотеки:**\n\n"
        "• **📚 Підручники** — перегляд матеріалів за категоріями та дисциплінами.\n"
        "• **🔎 Пошук матеріалів** — пошук за назвою або ключовим словом.\n"
        "• **📤 Запропонувати файл** — надіслати новий матеріал на перевірку адміністратору.\n\n"
        "Усі завантажені файли зберігаються в Telegram, тому їх можна відкривати та читати офлайн."
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user

    # Очищуємо старі стани при перемиканні головних пунктів меню
    if text in ["📚 Підручники", "🔎 Пошук матеріалів", "📤 Запропонувати файл", "ℹ️ Допомога", "⚙️ Адмін-панель"]:
        context.user_data.pop("waiting_for_search", None)
        context.user_data.pop("submitting", None)
        context.user_data.pop("admin_step", None)

    if text == "📚 Підручники":
        await show_categories(update, context)
    elif text == "🔎 Пошук матеріалів":
        context.user_data["waiting_for_search"] = True
        await update.message.reply_text("Введіть назву підручника, дисципліни або ключове слово для пошуку:")
    elif text == "📤 Запропонувати файл":
        context.user_data["submitting"] = True
        await update.message.reply_text(
            "Будь ласка, надішліть **PDF-файл** підручника або вкажіть посилання, а також вкажіть назву та дисципліну у підписі до повідомлення."
        )
    elif text == "⚙️ Адмін-панель" and user.id == ADMIN_ID:
        await show_admin_panel(update, context)
    elif context.user_data.get("waiting_for_search"):
        context.user_data["waiting_for_search"] = False
        await perform_search(update, context, text)
    elif context.user_data.get("submitting"):
        # Обробка пропозиції від студента
        await handle_student_submission(update, context)
    else:
        await update.message.reply_text("Скористайтеся кнопками меню нижче 👇", reply_markup=get_main_menu(user.id))


# --- РОЗДІЛ «ПІДРУЧНИКИ» ---

async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for cat in CATEGORIES.keys():
        keyboard.append([InlineKeyboardButton(cat, callback_data=f"cat_{cat}")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.message.edit_text("Оберіть категорію дисциплін:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Оберіть категорію дисциплін:", reply_markup=reply_markup)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("cat_"):
        category_name = data[4:]
        disciplines = CATEGORIES.get(category_name, [])
        keyboard = []
        for disc in disciplines:
            keyboard.append([InlineKeyboardButton(disc, callback_data=f"disc_{category_name}__{disc}")])
        keyboard.append([InlineKeyboardButton("⬅️ Назад до категорій", callback_data="back_to_cats")])
        await query.message.edit_text(f"Категорія: **{category_name}**\nОберіть дисципліну:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "back_to_cats":
        keyboard = []
        for cat in CATEGORIES.keys():
            keyboard.append([InlineKeyboardButton(cat, callback_data=f"cat_{cat}")])
        await query.message.edit_text("Оберіть категорію дисциплін:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("disc_"):
        remainder = data[5:]
        found_cat = None
        found_disc = None
        for cat, discs in CATEGORIES.items():
            if remainder.startswith(cat + "__"):
                found_cat = cat
                found_disc = remainder[len(cat) + 2:]
                break

        if found_cat and found_disc:
            books = await load_books_from_github()
            filtered_books = [b for b in books if b.get("category") == found_cat and b.get("discipline") == found_disc and b.get("approved", True)]
            
            if not filtered_books:
                text = f"Дисципліна: **{found_disc}**\n\nНаразі тут немає завантажених підручників."
                keyboard = [[InlineKeyboardButton("⬅️ Назад до дисциплін", callback_data=f"cat_{found_cat}")]]
                await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            else:
                await query.message.edit_text(f"Дисципліна: **{found_disc}**\nЗнайдено матеріалів: {len(filtered_books)}", parse_mode="Markdown")
                for book in filtered_books:
                    title = book.get("title", "Без назви")
                    file_id = book.get("file_id")
                    ext_link = book.get("external_link")

                    msg_text = f"📖 **{title}**\nДисципліна: {found_disc}"
                    if file_id:
                        await context.bot.send_document(chat_id=query.message.chat_id, document=file_id, caption=msg_text, parse_mode="Markdown")
                    elif ext_link:
                        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Відкрити посилання", url=ext_link)]])
                        await context.bot.send_message(chat_id=query.message.chat_id, text=msg_text, reply_markup=kb, parse_mode="Markdown")

    elif data.startswith("admin_approve_"):
        # Схвалення матеріалу адміном
        book_index = int(data.split("_")[2])
        books = await load_books_from_github()
        if 0 <= book_index < len(books):
            books[book_index]["approved"] = True
            success = await save_books_to_github(books, f"Approve book: {books[book_index].get('title')}")
            if success:
                await query.message.edit_text("✅ Матеріал успішно схвалено та додано до бібліотеки!")
            else:
                await query.message.edit_text("❌ Помилка збереження на GitHub.")


# --- ПОШУК ---

async def perform_search(update: Update, context: ContextTypes.DEFAULT_TYPE, keyword: str):
    books = await load_books_from_github()
    keyword_lower = keyword.lower()
    results = [
        b for b in books
        if (keyword_lower in b.get("title", "").lower() or keyword_lower in b.get("discipline", "").lower()) and b.get("approved", True)
    ]

    if not results:
        await update.message.reply_text(f"За запитом «{keyword}» нічого не знайдено.")
        return

    await update.message.reply_text(f"Результати пошуку за запитом «{keyword}» (знайдено: {len(results)}):")
    for book in results:
        title = book.get("title", "Без назви")
        disc = book.get("discipline", "")
        file_id = book.get("file_id")
        ext_link = book.get("external_link")

        msg_text = f"📖 **{title}**\nДисципліна: {disc}"
        if file_id:
            await update.message.reply_document(document=file_id, caption=msg_text, parse_mode="Markdown")
        elif ext_link:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Відкрити посилання", url=ext_link)]])
            await update.message.reply_text(msg_text, reply_markup=kb, parse_mode="Markdown")


# --- ПРОПОЗИЦІЇ ВІД СТУДЕНТІВ ---

async def handle_student_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    document = update.message.document
    text = update.message.text or update.message.caption or "Без назви"

    file_id = document.file_id if document else None
    ext_link = None
    if not file_id and update.message.text:
        words = update.message.text.split()
        for w in words:
            if w.startswith("http://") or w.startswith("https://"):
                ext_link = w
                break

    if not file_id and not ext_link:
        await update.message.reply_text("Будь ласка, надішліть PDF-файл або прикріпіть посилання.")
        return

    new_book = {
        "title": text,
        "category": "Загальні пропозиції",
        "discipline": "Не вказано",
        "file_id": file_id,
        "external_link": ext_link,
        "approved": False,
        "submitted_by": user.full_name,
    }

    books = await load_books_from_github()
    books.append(new_book)
    book_idx = len(books) - 1
    await save_books_to_github(books, f"Student submission by {user.full_name}")

    context.user_data["submitting"] = False
    await update.message.reply_text("Дякуємо! Ваша пропозиція надіслана адміністратору на перевірку.")

    # Надсилаємо сповіщення адміну
    if ADMIN_ID:
        admin_text = f"📥 **Нова пропозиція матеріалу!**\nВід: {user.full_name}\nНазва/Опис: {text}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Схвалити", callback_data=f"admin_approve_{book_idx}")]])
        if file_id:
            await context.bot.send_document(chat_id=ADMIN_ID, document=file_id, caption=admin_text, reply_markup=kb, parse_mode="Markdown")
        else:
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_text, reply_markup=kb, parse_mode="Markdown")


# --- АДМІН-ПАНЕЛЬ ---

async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📚 Список усіх матеріалів", callback_data="admin_list_books")],
    ]
    await update.message.reply_text("⚙️ **Панель адміністратора:**\nТут ви можете керувати контентом.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# --- ВЕБСЕРВЕР ДЛЯ RENDER ---

async def handle_web_request(request):
    return web.Response(text="BMFK Study Library Bot is running!")


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_web_request)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.getenv("PORT", "10000"))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Вебсервер запущено на порту {port}")


# --- ГОЛОВНА ФУНКЦІЯ ЗАПУСКУ ---

def main():
    if not BOT_TOKEN:
        logger.error("Помилка: BOT_TOKEN не встановлено у змінних середовища!")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    # Реєстрація обробників
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))
    application.add_handler(MessageHandler(filters.Document.ALL, text_router))
    application.add_handler(CallbackQueryHandler(handle_callback))

    # Запуск вебсерверу та бота разом
    loop = asyncio.get_event_loop()
    loop.create_task(start_web_server())

    logger.info("Бот запущено в режимі Polling...")
    application.run_polling()


if __name__ == "__main__":
    main()
