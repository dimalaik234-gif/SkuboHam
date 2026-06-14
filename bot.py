import os, asyncio, io, random, cv2, numpy as np
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ChatAction, ParseMode, DiceEmoji
from aiogram.types import BufferedInputFile
from gtts import gTTS
from PIL import Image, ImageEnhance

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

mafia_sessions = {}
user_rep = {}

# --- ВОССТАНОВЛЕННОЕ МЕНЮ (КАК РАНЬШЕ) ---
HELP_FULL = (
    "🤖 **Я анимированный интерактивный бот Amatka!**\n\n"
    "Вот что я умею делать в чатах:\n\n"
    "🕵️‍♂️ /mafia_start — Запустить игру в Мафию\n"
    "/join — Вступить в игру\n"
    "/mafia_distribute — Разослать роли в ЛС (анонимно!)\n\n"
    "✨ /animate_text <текст> — Красивая анимация вашего текста\n"
    "🖼 /jmih (ответом на фото) — Настоящий, мемный, агрессивный жмых!\n"
    "🗣 /say <текст> — Бот скажет текст В ГОЛОСОВОМ СООБЩЕНИИ\n\n"
    "🎲 **ИГРЫ И УТИЛИТЫ:**\n"
    "/casino — Крутить слот-машину\n"
    "/roulette — Русская рулетка\n"
    "/magic8 <вопрос> — Магический шар предсказаний\n"
    "/rep — Повысить репутацию ответом на сообщение\n"
    "/ping — Проверить связь\n"
    "/myid — Твой ID\n"
    "/whoami — Кто ты сегодня?\n\n"
    "📌 Чтобы вызвать это меню снова, используйте /help_amatka"
)

# --- ЖМЫХ (OpenCV) ---
def apply_hard_jmih(img_bytes):
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    rows, cols, _ = img.shape
    for i in range(rows):
        for j in range(cols):
            offset_x = int(35.0 * np.sin(2 * 3.14 * i / 120))
            offset_y = int(35.0 * np.cos(2 * 3.14 * j / 120))
            if i + offset_y < rows and j + offset_x < cols:
                img[i, j] = img[(i + offset_y) % rows, (j + offset_x) % cols]
    _, encoded = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 5])
    return encoded.tobytes()

# --- ОСНОВНЫЕ ХЕНДЛЕРЫ ---
@dp.message(Command("start", "help_amatka"))
async def cmd_start(message: types.Message):
    await message.answer(HELP_FULL, parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("jmih"))
async def cmd_jmih(message: types.Message):
    photo = message.photo[-1] if message.photo else (message.reply_to_message.photo[-1] if message.reply_to_message and message.reply_to_message.photo else None)
    if not photo: return await message.answer("❌ Отправь фото или ответь на него командой /jmih!")
    file = await bot.get_file(photo.file_id)
    buffer = io.BytesIO()
    await bot.download_file(file.file_path, buffer)
    await bot.send_chat_action(message.chat.id, action=ChatAction.UPLOAD_PHOTO)
    processed = apply_hard_jmih(buffer.getvalue())
    await message.answer_photo(BufferedInputFile(processed, "jmih.jpg"), caption="🥴 *Жмых активирован!*", parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("say"))
async def cmd_say(message: types.Message):
    text = message.text.replace("/say", "").strip()
    if not text: return await message.answer("Напиши текст!")
    await bot.send_chat_action(message.chat.id, action=ChatAction.RECORD_VOICE)
    tts = gTTS(text=text, lang='ru')
    audio = io.BytesIO()
    tts.write_to_fp(audio)
    audio.seek(0)
    await message.answer_voice(voice=BufferedInputFile(audio.read(), "voice.ogg"))

# --- МАФИЯ ---
@dp.message(Command("mafia_start"))
async def mafia_start(message: types.Message):
    mafia_sessions[message.chat.id] = {"players": []}
    await message.answer("🕵️‍♂️ Мафия создана! Жми /join")

@dp.message(Command("join"))
async def mafia_join(message: types.Message):
    if message.chat.id in mafia_sessions:
        players = mafia_sessions[message.chat.id]['players']
        if message.from_user.id not in [p['id'] for p in players]:
            players.append({'id': message.from_user.id, 'name': message.from_user.full_name})
            await message.reply(f"✅ {message.from_user.first_name} в деле!")

@dp.message(Command("mafia_distribute"))
async def distribute_roles(message: types.Message):
    players = mafia_sessions.get(message.chat.id, {}).get('players', [])
    if len(players) < 3: return await message.answer("Мало людей!")
    roles = ["Мафия", "Мирный", "Комиссар", "Доктор"] + ["Мирный"] * (len(players)-4)
    random.shuffle(roles)
    for i, p in enumerate(players):
        try:
            await bot.send_message(p['id'], f"Твоя роль: *{roles[i]}*", parse_mode=ParseMode.MARKDOWN)
        except:
            await message.answer(f"Не могу написать {p['name']} в ЛС!")
    await message.answer("🕵️‍♂️ Роли отправлены в личку! Никому не пались.")

@dp.message(Command("animate_text"))
async def cmd_animate(message: types.Message):
    text = message.text.replace("/animate_text", "").strip() or "Анимация..."
    sent = await message.answer("░")
    for i in range(len(text)+1):
        await sent.edit_text(f"{text[:i]}▋")
        await asyncio.sleep(0.15)
    await sent.edit_text(text)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
