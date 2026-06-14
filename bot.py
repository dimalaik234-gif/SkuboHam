import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- НАСТРОЙКИ ---
BOT_TOKEN = "8550577279:AAEu5YxshUMrEvQh3uUivHbEJxfENyvf8wQ"
ADMIN_ID = 7184353531  # Введите ваш Telegram ID численного формата (без кавычек)

# --- ИНИЦИАЛИЗАЦИЯ ---
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    # Таблица файлов
    cursor.execute('''CREATE TABLE IF NOT EXISTS files (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        owner_id INTEGER,
                        file_id TEXT,
                        text_content TEXT,
                        file_type TEXT,
                        password TEXT UNIQUE,
                        status TEXT DEFAULT 'approved')''')
    # Таблица пользователей и лимитов
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        is_banned INTEGER DEFAULT 0,
                        files_created INTEGER DEFAULT 0)''')
    # Системные настройки
    cursor.execute('''CREATE TABLE IF NOT EXISTS settings (
                        key TEXT PRIMARY KEY,
                        value TEXT)''')
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('max_files', '5')")
    conn.commit()
    conn.close()

def get_max_files():
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key='max_files'")
        res = cursor.fetchone()
        conn.close()
        return int(res[0]) if res else 5
    except Exception:
        return 5

# --- СОСТОЯНИЯ (FSM) ---
class Form(StatesGroup):
    waiting_for_search_password = State()
    waiting_for_file_or_text = State()
    waiting_for_create_password = State()
    waiting_for_ban_id = State()
    waiting_for_unban_id = State()
    waiting_for_new_limit = State()

# --- КЛАВИАТУРЫ ---
# --- КЛАВИАТУРА АДМИНКИ (УПРОЩЕННЫЙ ВАРИАНТ) ---
def get_admin_kb():
    # Создаем инлайн-кнопки строго по правилам aiogram 3.x
    btn_ban = InlineKeyboardButton(text="🚫 Заблокировать", callback_query_data="admin_ban")
    btn_unban = InlineKeyboardButton(text="✅ Разблокировать", callback_query_data="admin_unban")
    btn_limit = InlineKeyboardButton(text="⚙️ Изменить лимит", callback_query_data="admin_limit")
    btn_mod = InlineKeyboardButton(text="📝 Модерация файлов", callback_query_data="admin_mod")
    btn_all = InlineKeyboardButton(text="📊 Все файлы", callback_query_data="admin_all_files")
    
    # Собираем сетку кнопок
    keyboard = [
        [btn_ban, btn_unban],
        [btn_limit, btn_mod],
        [btn_all]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# --- ХЕНДЛЕР ВЫЗОВА АДМИНКИ ---
@dp.message(F.text == "👑 Админка")
async def admin_panel(message: Message):
    # Явное приведение к int для надежности сравнения ID
    if int(message.from_user.id) != int(ADMIN_ID):
        await message.answer("⚠️ У вас нет прав администратора.")
        return
        
    try:
        # Генерируем клавиатуру заново при вызове
        kb = get_admin_kb()
        await message.answer(
            text="Добро пожаловать в панель управления администратора:", 
            reply_markup=kb
        )
    except Exception as e:
        logging.error(f"Критическая ошибка вызова админки: {e}")
        await message.answer("Произошла ошибка при генерации меню админки.")


# --- МИДЛВАРЬ ДЛЯ ПРОВЕРКИ БАНА ---
@dp.message.outer_middleware()
async def check_ban_middleware(handler, event: Message, data: dict):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (event.from_user.id,))
    res = cursor.fetchone()
    conn.close()
    if res and res[0] == 1:
        await event.answer("❌ Вы заблокированы в этом боте.")
        return
    return await handler(event, data)

# --- ХЕНДЛЕРЫ ---

@dp.message(Command("start"))
async def start_cmd(message: Message):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.from_user.id,))
    conn.commit()
    conn.close()
    await message.answer("Привет! Выберите действие на клавиатуре:", reply_markup=get_main_kb(message.from_user.id))

# --- ПОИСК ФАЙЛА ---
@dp.message(F.text == "🔍 Найти файл")
async def search_file_start(message: Message, state: FSMContext):
    await message.answer("Введите пароль для поиска файла:")
    await state.set_state(Form.waiting_for_search_password)

@dp.message(Form.waiting_for_search_password)
async def search_file_process(message: Message, state: FSMContext):
    password = message.text.strip()
    await state.clear()

    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    
    # Ищем точное совпадение
    cursor.execute("SELECT file_id, text_content, file_type FROM files WHERE password = ? AND status = 'approved'", (password,))
    exact_match = cursor.fetchone()

    if exact_match:
        file_id, text_content, file_type = exact_match
        await message.answer("✅ Файл найден!")
        if file_type == "text":
            await message.answer(text_content)
        elif file_type == "photo":
            await message.answer_photo(file_id, caption=text_content)
        elif file_type == "document":
            await message.answer_document(file_id, caption=text_content)
    else:
        # Ищем похожие пароли (LIKE)
        cursor.execute("SELECT password FROM files WHERE password LIKE ? AND status = 'approved' LIMIT 5", (f"%{password}%",))
        similar = cursor.fetchall()
        
        if similar:
            sim_list = "\n".join([f"- `{p[0]}`" for p in similar])
            # Картинка заглушка для ошибки
            error_img = "https://itsm.expert/wp-content/uploads/2021/11/404-error.png"
            await message.answer_photo(
                photo=error_img,
                caption=f"❌ Точное совпадение не найдено.\n\nПохожие пароли:\n{sim_list}\n\nПопробуйте ввести заново.",
                parse_mode="Markdown"
            )
        else:
            await message.answer("❌ Файл с таким или похожим паролем не найден.")
    conn.close()

# --- СОЗДАНИЕ ФАЙЛА ---
@dp.message(F.text == "➕ Создать файл")
async def create_file_start(message: Message, state: FSMContext):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT files_created FROM users WHERE user_id = ?", (message.from_user.id,))
    res = cursor.fetchone()
    count = res[0] if res else 0
    conn.close()

    if count >= get_max_files():
        await message.answer(f"❌ Вы достигли лимита на создание файлов ({get_max_files()} шт).")
        return

    await message.answer("Отправьте мне любой файл, фото или текстовое сообщение:")
    await state.set_state(Form.waiting_for_file_or_text)

@dp.message(Form.waiting_for_file_or_text)
async def process_file_drop(message: Message, state: FSMContext):
    file_id = None
    text_content = None
    file_type = "text"

    if message.text:
        text_content = message.text
        file_type = "text"
    elif message.photo:
        file_id = message.photo[-1].file_id
        text_content = message.caption
        file_type = "photo"
    elif message.document:
        file_id = message.document.file_id
        text_content = message.caption
        file_type = "document"
    else:
        await message.answer("⚠️ Пожалуйста, отправьте текст, фото или документ.")
        return

    await state.update_data(file_id=file_id, text_content=text_content, file_type=file_type)
    await message.answer("Теперь придумайте и отправьте уникальный пароль для этого файла:")
    await state.set_state(Form.waiting_for_create_password)

@dp.message(Form.waiting_for_create_password)
async def process_save_password(message: Message, state: FSMContext):
    password = message.text.strip()
    data = await state.get_data()
    await state.clear()

    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO files (owner_id, file_id, text_content, file_type, password) VALUES (?, ?, ?, ?, ?)",
                       (message.from_user.id, data['file_id'], data['text_content'], data['file_type'], password))
        cursor.execute("UPDATE users SET files_created = files_created + 1 WHERE user_id = ?", (message.from_user.id,))
        conn.commit()
        await message.answer(f"🎉 Файл успешно сохранен! Пароль для доступа: `{password}`", parse_mode="Markdown")
    except sqlite3.IntegrityError:
        await message.answer("❌ Этот пароль уже занят. Попробуйте создать файл заново с другим паролем.")
    finally:
        conn.close()

# --- АДМИН ПАНЕЛЬ ---
@dp.message(F.text == "👑 Админка")
async def admin_panel(message: Message):
    if int(message.from_user.id) != int(ADMIN_ID):
        await message.answer("⚠️ У вас нет прав администратора.")
        return
    await message.answer("Добро пожаловать в панель управления:", reply_markup=get_admin_kb())

@dp.callback_query(F.data == "admin_ban")
async def admin_ban_start(call: CallbackQuery, state: FSMContext):
    if int(call.from_user.id) != int(ADMIN_ID): 
        await call.answer("Отказано в доступе", show_alert=True)
        return
    await call.message.answer("Введите Telegram ID пользователя для блокировки:")
    await state.set_state(Form.waiting_for_ban_id)
    await call.answer()

@dp.message(Form.waiting_for_ban_id)
async def admin_ban_proc(message: Message, state: FSMContext):
    if int(message.from_user.id) != int(ADMIN_ID): return
    try:
        uid = int(message.text)
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO users (user_id, is_banned) VALUES (?, 1)", (uid,))
        conn.commit()
        conn.close()
        await message.answer(f"🚫 Пользователь {uid} успешно заблокирован.")
    except ValueError:
        await message.answer("Вводите только цифры (ID).")
    await state.clear()

@dp.callback_query(F.data == "admin_unban")
async def admin_unban_start(call: CallbackQuery, state: FSMContext):
    if int(call.from_user.id) != int(ADMIN_ID): return
    await call.message.answer("Введите Telegram ID пользователя для разблокировки:")
    await state.set_state(Form.waiting_for_unban_id)
    await call.answer()

@dp.message(Form.waiting_for_unban_id)
async def admin_unban_proc(message: Message, state: FSMContext):
    if int(message.from_user.id) != int(ADMIN_ID): return
    try:
        uid = int(message.text)
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (uid,))
        conn.commit()
        conn.close()
        await message.answer(f"✅ Пользователь {uid} разблокирован.")
    except ValueError:
        await message.answer("Вводите только цифры (ID).")
    await state.clear()

@dp.callback_query(F.data == "admin_limit")
async def admin_limit_start(call: CallbackQuery, state: FSMContext):
    if int(call.from_user.id) != int(ADMIN_ID): return
    await call.message.answer(f"Текущий лимит: {get_max_files()} файлов. Введите новый лимит:")
    await state.set_state(Form.waiting_for_new_limit)
    await call.answer()

@dp.message(Form.waiting_for_new_limit)
async def admin_limit_proc(message: Message, state: FSMContext):
    if int(message.from_user.id) != int(ADMIN_ID): return
    try:
        new_lim = int(message.text)
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE settings SET value = ? WHERE key = 'max_files'", (str(new_lim),))
        conn.commit()
        conn.close()
        await message.answer(f"⚙️ Лимит успешно изменен на {new_lim}")
    except ValueError:
        await message.answer("Введите целое число.")
    await state.clear()

@dp.callback_query(F.data == "admin_all_files")
async def admin_all_files(call: CallbackQuery):
    if int(call.from_user.id) != int(ADMIN_ID): 
        await call.answer("Отказано в доступе", show_alert=True)
        return
        
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, password, file_type FROM files")
        files = cursor.fetchall()
        conn.close()

        if not files:
            await call.message.answer("База файлов пуста.")
            await call.answer()
            return

        text = "📂 **Список всех файлов:**\n\n"
        keyboard_buttons = []
        
        for f in files:
            fid, pwd, ftype = f
            text += f"ID: {fid} | Тип: {ftype} | Пароль: `{pwd}`\n"
            keyboard_buttons.append([
                InlineKeyboardButton(text=f"🗑 Удалить {pwd}", callback_query_data=f"del_{fid}")
            ])
        
        kb = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        await call.message.answer(text, reply_markup=kb, parse_mode="Markdown")
        
    except Exception as e:
        logging.error(f"Ошибка в админке: {e}")
        await call.message.answer("Произошла ошибка при чтении БД.")
        
    await call.answer()

@dp.callback_query(F.data.startswith("del_"))
async def admin_delete_file(call: CallbackQuery):
    if int(call.from_user.id) != int(ADMIN_ID): return
    file_id_db = int(call.data.split("_")[1])
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM files WHERE id = ?", (file_id_db,))
    conn.commit()
    conn.close()
    await call.message.answer(f"🗑 Файл с ID {file_id_db} удален из базы.")
    await call.answer()

@dp.callback_query(F.data == "admin_mod")
async def admin_mod(call: CallbackQuery):
    await call.message.answer("Все файлы по умолчанию одобрены. Используйте вкладку 'Все файлы' для удаления нежелательного контента.")
    await call.answer()

# --- ЗАПУСК БОТА ---
async def main():
    init_db()
    print("Бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
