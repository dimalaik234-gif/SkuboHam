import os
import asyncio
import sys
import io
import random
import cv2
import numpy as np
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ChatAction, ParseMode, DiceEmoji
from aiogram.types import BufferedInputFile
from gtts import gTTS
from PIL import Image, ImageEnhance

# Токен из окружения
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    print("Ошибка: Переменная окружения BOT_TOKEN не задана!")
    sys.exit(1)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Хранилище для мафии и репутации
mafia_sessions = {}
user_rep = {}

# --- 1. АГРЕССИВНЫЙ ЖМЫХ (OpenCV) ---
def apply_hard_jmih(img_bytes):
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    rows, cols, _ = img.shape
    
    # Создаем мемную деформацию
    # Используем синусоиды для "плывущего" эффекта, как на твоих примерах
    for i in range(rows):
        for j in range(cols):
            # Магия смещения пикселей для "потекшего" лица
            offset_x = int(30.0 * np.sin(2 * 3.14 * i / 100))
            offset_y = int(30.0 * np.cos(2 * 3.14 * j / 100))
            if i + offset_y < rows and j + offset_x < cols:
                img[i, j] = img[(i + offset_y) % rows, (j + offset_x) % cols]
    
    # Добавляем жесткое сжатие JPEG для артефактов
    _, encoded_img = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 5])
    return encoded_img.tobytes()

@dp.message(Command("jmih"))
async def cmd_jmih(message: types.Message):
    # Работает с фото из сообщения или ответом
    photo = message.photo[-1] if message.photo else (message.reply_to_message.photo[-1] if message.reply_to_message and message.reply_to_message.photo else None)
    if not photo:
        return await message.answer("Отправь фото или ответь на него командой /jmih!")
    
    file = await bot.get_file(photo.file_id)
    buffer = io.BytesIO()
    await bot.download_file(file.file_path, buffer)
    
    await bot.send_chat_action(message.chat.id, action=ChatAction.UPLOAD_PHOTO)
    processed = apply_hard_jmih(buffer.getvalue())
    await message.answer_photo(BufferedInputFile(processed, "jmih.jpg"), caption="Вот это настоящий жмых! 🥴")

# --- 2. ГОЛОСОВОЙ SAY ---
@dp.message(Command("say"))
async def cmd_say(message: types.Message):
    text = message.text.replace("/say", "").strip()
    if not text: return await message.answer("Напиши текст!")
    
    await bot.send_chat_action(message.chat.id, action=ChatAction.RECORD_VOICE)
    tts = gTTS(text=text, lang='ru')
    audio = io.BytesIO()
    tts.write_to_fp(audio)
    audio.seek(0)
    await message.answer_voice(BufferedInputFile(audio.read(), "voice.ogg"))

# --- 3. АНОНИМНАЯ МАФИЯ ---
@dp.message(Command("mafia_start"))
async def mafia_start(message: types.Message):
    mafia_sessions[message.chat.id] = {"players": []}
    await message.answer("🕵️‍♂️ Мафия запущена! Пишите `/join` чтобы участвовать.")

@dp.message(Command("join"))
async def mafia_join(message: types.Message):
    if message.chat.id in mafia_sessions:
        players = mafia_sessions[message.chat.id]['players']
        if message.from_user.id not in [p['id'] for p in players]:
            players.append({'id': message.from_user.id, 'name': message.from_user.full_name})
            await message.reply(f"{message.from_user.first_name} в игре!")

@dp.message(Command("mafia_distribute"))
async def distribute_roles(message: types.Message):
    players = mafia_sessions.get(message.chat.id, {}).get('players', [])
    if len(players) < 3: return await message.answer("Мало игроков!")
    roles = ["Мафия", "Мирный", "Комиссар", "Доктор"] + ["Мирный"] * (len(players)-4)
    random.shuffle(roles)
    for i, p in enumerate(players):
        try:
            await bot.send_message(p['id'], f"Твоя роль: *{roles[i]}*", parse_mode=ParseMode.MARKDOWN)
        except:
            await message.answer(f"Не могу написать {p['name']} в ЛС!")
    await message.answer("🕵️‍♂️ Роли разосланы в ЛС!")

# --- 4. МИНИ-ИГРЫ И УТИЛИТЫ ---
@dp.message(Command("casino"))
async def cmd_casino(message: types.Message):
    msg = await message.answer_dice(emoji=DiceEmoji.SLOT_MACHINE)
    await asyncio.sleep(2)
    if msg.dice.value == 64: await message.reply("🎰 ДЖЕКПОТ!")
    else: await message.reply("Попробуй еще раз!")

@dp.message(Command("rep"))
async def cmd_rep(message: types.Message):
    if message.reply_to_message:
        tid = message.reply_to_message.from_user.id
        user_rep[tid] = user_rep.get(tid, 0) + 1
        await message.answer(f"Репутация повышена! Теперь: {user_rep[tid]}")

@dp.message(Command("ping"))
async def cmd_ping(message: types.Message): await message.reply("Pong!")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привет! Я Amatka. Мои команды: /mafia_start, /join, /mafia_distribute, /jmih, /say, /casino, /rep, /ping")

# --- ЗАПУСК ---
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
import os
import asyncio
import sys
import io
import random
import cv2
import numpy as np
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ChatAction, ParseMode, DiceEmoji
from aiogram.types import BufferedInputFile
from gtts import gTTS
from PIL import Image, ImageEnhance

# Токен из окружения
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    print("Ошибка: Переменная окружения BOT_TOKEN не задана!")
    sys.exit(1)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Хранилище для мафии и репутации
mafia_sessions = {}
user_rep = {}

# --- 1. АГРЕССИВНЫЙ ЖМЫХ (OpenCV) ---
def apply_hard_jmih(img_bytes):
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    rows, cols, _ = img.shape
    
    # Создаем мемную деформацию
    # Используем синусоиды для "плывущего" эффекта, как на твоих примерах
    for i in range(rows):
        for j in range(cols):
            # Магия смещения пикселей для "потекшего" лица
            offset_x = int(30.0 * np.sin(2 * 3.14 * i / 100))
            offset_y = int(30.0 * np.cos(2 * 3.14 * j / 100))
            if i + offset_y < rows and j + offset_x < cols:
                img[i, j] = img[(i + offset_y) % rows, (j + offset_x) % cols]
    
    # Добавляем жесткое сжатие JPEG для артефактов
    _, encoded_img = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 5])
    return encoded_img.tobytes()

@dp.message(Command("jmih"))
async def cmd_jmih(message: types.Message):
    # Работает с фото из сообщения или ответом
    photo = message.photo[-1] if message.photo else (message.reply_to_message.photo[-1] if message.reply_to_message and message.reply_to_message.photo else None)
    if not photo:
        return await message.answer("Отправь фото или ответь на него командой /jmih!")
    
    file = await bot.get_file(photo.file_id)
    buffer = io.BytesIO()
    await bot.download_file(file.file_path, buffer)
    
    await bot.send_chat_action(message.chat.id, action=ChatAction.UPLOAD_PHOTO)
    processed = apply_hard_jmih(buffer.getvalue())
    await message.answer_photo(BufferedInputFile(processed, "jmih.jpg"), caption="Вот это настоящий жмых! 🥴")

# --- 2. ГОЛОСОВОЙ SAY ---
@dp.message(Command("say"))
async def cmd_say(message: types.Message):
    text = message.text.replace("/say", "").strip()
    if not text: return await message.answer("Напиши текст!")
    
    await bot.send_chat_action(message.chat.id, action=ChatAction.RECORD_VOICE)
    tts = gTTS(text=text, lang='ru')
    audio = io.BytesIO()
    tts.write_to_fp(audio)
    audio.seek(0)
    await message.answer_voice(BufferedInputFile(audio.read(), "voice.ogg"))

# --- 3. АНОНИМНАЯ МАФИЯ ---
@dp.message(Command("mafia_start"))
async def mafia_start(message: types.Message):
    mafia_sessions[message.chat.id] = {"players": []}
    await message.answer("🕵️‍♂️ Мафия запущена! Пишите `/join` чтобы участвовать.")

@dp.message(Command("join"))
async def mafia_join(message: types.Message):
    if message.chat.id in mafia_sessions:
        players = mafia_sessions[message.chat.id]['players']
        if message.from_user.id not in [p['id'] for p in players]:
            players.append({'id': message.from_user.id, 'name': message.from_user.full_name})
            await message.reply(f"{message.from_user.first_name} в игре!")

@dp.message(Command("mafia_distribute"))
async def distribute_roles(message: types.Message):
    players = mafia_sessions.get(message.chat.id, {}).get('players', [])
    if len(players) < 3: return await message.answer("Мало игроков!")
    roles = ["Мафия", "Мирный", "Комиссар", "Доктор"] + ["Мирный"] * (len(players)-4)
    random.shuffle(roles)
    for i, p in enumerate(players):
        try:
            await bot.send_message(p['id'], f"Твоя роль: *{roles[i]}*", parse_mode=ParseMode.MARKDOWN)
        except:
            await message.answer(f"Не могу написать {p['name']} в ЛС!")
    await message.answer("🕵️‍♂️ Роли разосланы в ЛС!")

# --- 4. МИНИ-ИГРЫ И УТИЛИТЫ ---
@dp.message(Command("casino"))
async def cmd_casino(message: types.Message):
    msg = await message.answer_dice(emoji=DiceEmoji.SLOT_MACHINE)
    await asyncio.sleep(2)
    if msg.dice.value == 64: await message.reply("🎰 ДЖЕКПОТ!")
    else: await message.reply("Попробуй еще раз!")

@dp.message(Command("rep"))
async def cmd_rep(message: types.Message):
    if message.reply_to_message:
        tid = message.reply_to_message.from_user.id
        user_rep[tid] = user_rep.get(tid, 0) + 1
        await message.answer(f"Репутация повышена! Теперь: {user_rep[tid]}")

@dp.message(Command("ping"))
async def cmd_ping(message: types.Message): await message.reply("Pong!")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привет! Я Amatka. Мои команды: /mafia_start, /join, /mafia_distribute, /jmih, /say, /casino, /rep, /ping")

# --- ЗАПУСК ---
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
