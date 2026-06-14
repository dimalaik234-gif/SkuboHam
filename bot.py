import asyncio
import sqlite3
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton, 
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)

# --- НАСТРОЙКИ (Берутся из панели хостинга Bothost) ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

if not BOT_TOKEN:
    raise ValueError("ОШИБКА: Переменная окружения BOT_TOKEN не задана в панели Bothost!")

# --- ИНИЦИАЛИЗАЦИЯ ---
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect("storage.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id TEXT,
            file_type TEXT,
            text_content TEXT,
            password TEXT UNIQUE
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value INTEGER
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS banned_users (
            user_id INTEGER PRIMARY KEY
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('file_limit', 10)")
    conn.commit()
    conn.close()

# --- КЛАВИАТУРЫ ---
def get_main_kb(user_id: int):
    buttons = [
        [KeyboardButton(text="🔍 Найти файл"), KeyboardButton(text="➕ Создать файл")]
    ]
    if user_id == ADMIN_ID:
        buttons.append([KeyboardButton(text="👑 Админка")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Чат-блок (Бан)", callback_query_data="admin_ban")],
        [InlineKeyboardButton(text="⚙️ Изменить лимиты", callback_query_data="admin_limits")],
        [InlineKeyboardButton(text="📂 Все файлы / Модерация", callback_query_data="admin_files_0")]
    ])

# --- СОСТОЯНИЯ (FSM) ---
class SearchState(StatesGroup):
    wait_password = State()

class CreateState(StatesGroup):
    wait_content = State()
    wait_password = State()

class AdminState(StatesGroup):
    wait_ban_id = State()
    wait_limit = State()
    wait_edit_pass = State()

# --- МИДЛВАРЬ ДЛЯ ПРОВЕРКИ БАНА ---
@dp.message.middleware()
async def check_ban_middleware(handler, event: Message, data: dict):
    conn = sqlite3.connect("storage.db")
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM banned_users WHERE user_id = ?", (event.from_user.id,))
    banned = cursor.fetchone()
    conn.close()
    
    if banned:
        await event.answer("❌ Вы заблокированы администратором.")
        return
    return await handler(event, data)

# --- ХЕНДЛЕРЫ НАЧАЛА ---
@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"Привет, {message.from_user.first_name}! Я бот-хранилище файлов по паролям.",
        reply_markup=get_main_kb(message.from_user.id)
    )

# ================= Команда: НАЙТИ ФАЙЛ =================
@dp.message(F.text == "🔍 Найти файл")
async def search_file_start(message: Message, state: FSMContext):
    await message.answer("Введите пароль для поиска файла:")
    await state.set_state(SearchState.wait_password)

@dp.message(SearchState.wait_password)
async def search_file_process(message: Message, state: FSMContext):
    password = message.text.strip()
    await state.clear()
    
    conn = sqlite3.connect("storage.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT file_id, file_type, text_content FROM files WHERE password = ?", (password,))
    exact_match = cursor.fetchone()
    
    if exact_match:
        file_id, file_type, text_content = exact_match
        await message.answer("✅ Файл найден!")
        if file_type == 'text':
            await message.answer(text_content)
        elif file_type == 'photo':
            await message.answer_photo(file_id)
        elif file_type == 'document':
            await message.answer_document(file_id)
    else:
        cursor.execute("SELECT password FROM files WHERE password LIKE ?", (f"%{password}%",))
        similar = cursor.fetchall()
        
        if similar:
            suggestions = "\n".join([f"🔹 `{p[0]}`" for p in similar[:5]])
            await message.answer(
                f"❌ Точное совпадение не найдено.\n\nПохожие пароли:\n{suggestions}\n\n"
                "Попробуйте ввести заново, нажав кнопку «🔍 Найти файл».", 
                parse_mode="Markdown"
            )
        else:
            await message.answer("❌ Файл с таким или похожим паролем не найден.")
            
    conn.close()

# ================= Команда: СОЗДАТЬ ФАЙЛ =================
@dp.message(F.text == "➕ Создать файл")
async def create_file_start(message: Message, state: FSMContext):
    conn = sqlite3.connect("storage.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM files")
    total_files = cursor.fetchone()[0]
    cursor.execute("SELECT value FROM settings WHERE key = 'file_limit'")
    limit = cursor.fetchone()[0]
    conn.close()
    
    if total_files >= limit:
        await message.answer(f"⚠️ Достигнут общий лимит файлов в системе ({limit}). Создание невозможно.")
        return

    await message.answer("Отправьте мне любой файл (картинку, документ) или текстовое сообщение:")
    await state.set_state(CreateState.wait_content)

@dp.message(CreateState.wait_content)
async def create_file_content(message: Message, state: FSMContext):
    file_id = None
    file_type = 'text'
    text_content = None

    if message.photo:
        file_id = message.photo[-1].file_id
        file_type = 'photo'
    elif message.document:
        file_id = message.document.file_id
        file_type = 'document'
    elif message.text:
        text_content = message.text
        file_type = 'text'
    else:
        await message.answer("❌ Данный тип контента не поддерживается. Отправьте текст, фото или документ.")
        return

    await state.update_data(file_id=file_id, file_type=file_type, text_content=text_content)
    await message.answer("🔑 Теперь придумайте и отправьте уникальный пароль для этого файла:")
    await state.set_state(CreateState.wait_password)

@dp.message(CreateState.wait_password)
async def create_file_password(message: Message, state: FSMContext):
    password = message.text.strip()
    data = await state.get_data()
    await state.clear()
    
    conn = sqlite3.connect("storage.db")
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO files (file_id, file_type, text_content, password) VALUES (?, ?, ?, ?)",
            (data['file_id'], data['file_type'], data['text_content'], password)
        )
        conn.commit()
        await message.answer(f"🎉 Файл успешно сохранен!\nПароль для доступа: `{password}`", parse_mode="Markdown")
    except sqlite3.IntegrityError:
        await message
