import os
import asyncio
import io
import random
import cv2
import numpy as np
import sys
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ChatAction, ParseMode, DiceEmoji
from aiogram.types import BufferedInputFile
from gtts import gTTS

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    print("Ошибка: Переменная окружения BOT_TOKEN не задана!", file=sys.stderr)
    sys.exit(1)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Хранилища данных
mafia_sessions = {}
user_rep = {}

# --- МЕНЮ БОТА ---
HELP_FULL = (
    "🤖 **Я интерактивный бот Amatka!**\n\n"
    "Вот что я умею:\n\n"
    "🕵️‍♂️ **МАФИЯ:**\n"
    "`/mafia_start` — Создать игру\n"
    "`/join` — Вступить в игру\n"
    "`/mafia_distribute` — Раздать роли в ЛС\n\n"
    "✨ **МЕДИА:**\n"
    "`/animate_text <текст>` — Анимированная печать\n"
    "`/jmih` *(ответом на фото)* — Настоящий мемный жмых!\n"
    "`/say <текст>` — Озвучить текст голосом\n\n"
    "🎲 **ИГРЫ И ФАН:**\n"
    "`/casino` — Крутить слот-машину\n"
    "`/roulette` — Русская рулетка\n"
    "`/magic8 <вопрос>` — Магический шар\n"
    "`/whoami` — Кто ты сегодня?\n\n"
    "⚙️ **УТИЛИТЫ:**\n"
    "`/rep` *(ответом)* — Повысить репутацию\n"
    "`/ping` — Проверка связи\n"
    "`/myid` — Узнать свой ID\n\n"
    "📌 Меню: `/help_amatka`"
)

# --- БЫСТРЫЙ И ЖЕСТКИЙ ЖМЫХ (OpenCV + NumPy) ---
def apply_hard_jmih(img_bytes):
    # Загружаем картинку
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # Чтобы бот не вис на 4К фото, делаем ресайз
    max_size = 600
    h, w = img.shape[:2]
    if max(h, w) > max_size:
        scale = max_size / max(h, w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)))

    rows, cols, _ = img.shape
    
    # Векторная магия для создания "поплывшего" лица (Warp-эффект)
    x = np.arange(cols)
    y = np.arange(rows)
    X, Y = np.meshgrid(x, y)

    offset_X = (30.0 * np.sin(2 * 3.14 * Y / 100)).astype(int)
    offset_Y = (30.0 * np.cos(2 * 3.14 * X / 100)).astype(int)

    map_x = np.clip(X + offset_X, 0, cols - 1).astype(np.float32)
    map_y = np.clip(Y + offset_Y, 0, rows - 1).astype(np.float32)

    distorted = cv2.remap(img, map_x, map_y, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    
    # Дико шакалим качество (до 5 из 100)
    _, encoded = cv2.imencode('.jpg', distorted, [int(cv2.IMWRITE_JPEG_QUALITY), 5])
    return encoded.tobytes()

# ==========================================
# ХЕНДЛЕРЫ КОМАНД (ТУТ РАБОТАЕТ ВСЁ)
# ==========================================

@dp.message(Command("start", "help_amatka"))
async def cmd_start(message: types.Message):
    await message.answer(HELP_FULL, parse_mode=ParseMode.MARKDOWN)

# --- ФОТО И ГОЛОС ---
@dp.message(Command("jmih"))
async def cmd_jmih(message: types.Message):
    photo = message.photo[-1] if message.photo else (message.reply_to_message.photo[-1] if message.reply_to_message and message.reply_to_message.photo else None)
    if not photo:
        return await message.answer("❌ Отправь фото или ответь на него командой `/jmih`!", parse_mode=ParseMode.MARKDOWN)
    
    await bot.send_chat_action(message.chat.id, action=ChatAction.UPLOAD_PHOTO)
    file = await bot.get_file(photo.file_id)
    buffer = io.BytesIO()
    await bot.download_file(file.file_path, buffer)
    
    try:
        processed = apply_hard_jmih(buffer.getvalue())
        await message.answer_photo(BufferedInputFile(processed, "jmih.jpg"), caption="🥴 *Жмых активирован!*", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await message.answer("❌ Ошибка жмыха. Фото слишком странное!")

@dp.message(Command("say"))
async def cmd_say(message: types.Message):
    text = message.text.replace("/say", "").strip()
    if not text:
        return await message.answer("Напиши текст, который нужно сказать!")
    
    await bot.send_chat_action(message.chat.id, action=ChatAction.RECORD_VOICE)
    try:
        tts = gTTS(text=text, lang='ru')
        audio = io.BytesIO()
        tts.write_to_fp(audio)
        audio.seek(0)
        await message.answer_voice(voice=BufferedInputFile(audio.read(), "voice.ogg"))
    except:
        await message.answer("❌ Не удалось сгенерировать голос.")

@dp.message(Command("animate_text"))
async def cmd_animate(message: types.Message):
    text = message.text.replace("/animate_text", "").strip()
    if not text:
        text = "Анимация работает!"
    
    sent = await message.answer("░")
    for i in range(1, len(text) + 1):
        try:
            await sent.edit_text(f"{text[:i]}▋")
            await asyncio.sleep(0.15)
        except:
            pass # Игнор ошибок лимита телеграма
    try:
        await sent.edit_text(text)
    except:
        pass

# --- АНОНИМНАЯ МАФИЯ ---
@dp.message(Command("mafia_start"))
async def mafia_start(message: types.Message):
    mafia_sessions[message.chat.id] = {"players": []}
    await message.answer("🕵️‍♂️ Игра в Мафию создана! Пишите `/join` чтобы участвовать.", parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("join"))
async def mafia_join(message: types.Message):
    if message.chat.id in mafia_sessions:
        players = mafia_sessions[message.chat.id]['players']
        if message.from_user.id not in [p['id'] for p in players]:
            players.append({'id': message.from_user.id, 'name': message.from_user.full_name})
            await message.reply(f"✅ {message.from_user.first_name} вступил(а) в игру! (Игроков: {len(players)})")

@dp.message(Command("mafia_distribute"))
async def distribute_roles(message: types.Message):
    players = mafia_sessions.get(message.chat.id, {}).get('players', [])
    if len(players) < 3:
        return await message.answer("❌ Для мафии нужно минимум 3 игрока!")
    
    roles = ["Мафия", "Мирный", "Комиссар", "Доктор"] + ["Мирный"] * (len(players) - 4)
    random.shuffle(roles)
    
    for i, p in enumerate(players):
        try:
            await bot.send_message(p['id'], f"🤫 Твоя роль в игре: *{roles[i]}*\nНикому не говори!", parse_mode=ParseMode.MARKDOWN)
        except:
            await message.answer(f"⚠️ Не смог отправить роль игроку {p['name']}. Ему нужно написать мне в личные сообщения `/start`.")
            
    await message.answer("🕵️‍♂️ **Роли успешно разосланы всем в личные сообщения!** Игра началась.", parse_mode=ParseMode.MARKDOWN)

# --- ИГРЫ И ФАН ---
@dp.message(Command("casino"))
async def cmd_casino(message: types.Message):
    msg = await message.answer_dice(emoji=DiceEmoji.SLOT_MACHINE)
    await asyncio.sleep(2)
    if msg.dice.value == 64:
        await message.reply("🎰 **ДЖЕКПОТ!!! 777! ТЫ СОРВАЛ КУШ!** 🎉", parse_mode=ParseMode.MARKDOWN)
    elif msg.dice.value in [1, 22, 43]:
        await message.reply("✨ Утешительный приз! Три одинаковых символа!")
    else:
        await message.reply("Эх, не повезло. Попробуй еще раз! 💸")

@dp.message(Command("roulette"))
async def cmd_roulette(message: types.Message):
    await message.answer("🔄 *Крутит барабан револьвера...*", parse_mode=ParseMode.MARKDOWN)
    await asyncio.sleep(1.5)
    if random.randint(1, 6) == 1:
        await message.reply("💥 **БАХ!** Ты проиграл. (Земля пухом)", parse_mode=ParseMode.MARKDOWN)
    else:
        await message.reply("💨 *Щелк.* Повезло, пустой. Живи пока.", parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("magic8"))
async def cmd_magic8(message: types.Message):
    question = message.text.replace("/magic8", "").strip()
    if not question:
        return await message.reply("🎱 Задай вопрос после команды!")
    answers = ["Бесспорно 🟢", "Определённо да 🟢", "Знаки говорят — да 🟡", "Спроси позже ⚪", "Мой ответ — нет 🔴", "Весьма сомнительно 🔴"]
    await message.reply(f"🎱 **Вопрос:** {question}\n🔮 **Ответ:** {random.choice(answers)}", parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("whoami"))
async def cmd_whoami(message: types.Message):
    roles = ["мемный жмых 🥴", "строгий админ 👑", "мирный житель 👨‍🌾", "суетолог 🌪", "батя 🧔‍♂️", "пелемень 🥟", "нейросеть 🤖", "гигачад 🗿"]
    await message.reply(f"Сегодня ты — **{random.choice(roles)}**!", parse_mode=ParseMode.MARKDOWN)

# --- УТИЛИТЫ ---
@dp.message(Command("rep"))
async def cmd_rep(message: types.Message):
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        target_name = message.reply_to_message.from_user.first_name
        user_rep[target_id] = user_rep.get(target_id, 0) + 1
        await message.answer(f"📈 Репутация пользователя **{target_name}** повышена!\nТекущая репа: {user_rep[target_id]}", parse_mode=ParseMode.MARKDOWN)
    else:
        await message.answer("⚠️ Эта команда работает только если ответить на чужое сообщение!")

@dp.message(Command("ping"))
async def cmd_ping(message: types.Message):
    await message.reply("🏓 **Pong!** Бот работает исправно.", parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("myid"))
async def cmd_myid(message: types.Message):
    await message.reply(f"👤 Твой ID: `{message.from_user.id}`\n💬 ID чата: `{message.chat.id}`", parse_mode=ParseMode.MARKDOWN)

# --- ЗАПУСК ---
async def main():
    print("Amatka Bot v3.0 (Полная версия) запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
