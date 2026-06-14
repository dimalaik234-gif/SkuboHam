import os
import asyncio
import sys
import io
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ChatAction, ParseMode, DiceEmoji
from aiogram.types import BufferedInputFile

# Для мемного жмыха
from PIL import Image, ImageEnhance, ImageOps

# Для голосовых сообщений
from gtts import gTTS

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    print("Ошибка: Переменная окружения BOT_TOKEN не задана!", file=sys.stderr)
    sys.exit(1)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ТЕКСТ СПРАВКИ И ПРИВЕТСТВИЯ ---
HELP_TEXT_BODY = (
    "🎮 **МИНИ-ИГРЫ:**\n"
    "🎲 `/casino` — Крутить слот-машину (выпадет ли джекпот?)\n"
    "🔫 `/roulette` — Русская рулетка\n"
    "🎱 `/magic8 <вопрос>` — Магический шар предсказаний\n"
    "🎭 `/whoami` — Кто ты сегодня?\n"
    "🕵️‍♂️ `/mafia_amatka` — Узнать свою случайную роль в Мафии\n\n"
    "✨ **ФИШКИ БОТА:**\n"
    "📝 `/animate_text <текст>` — Сделать живую анимацию текста\n"
    "🖼 `/jmih` (ответом на фото) — Агрессивный мемный жмых!\n"
    "🗣 `/say <текст>` — Бот скажет текст **В ГОЛОСОВОМ СООБЩЕНИИ**\n\n"
    "⚙️ **УТИЛИТЫ:**\n"
    "🏓 `/ping` — Проверить, работает ли бот\n"
    "🆔 `/myid` — Узнать свой Telegram ID"
)

async def get_main_menu_text(user_first_name=""):
    greeting = f"👋 Привет, {user_first_name}!\n\n" if user_first_name else "👋 Привет всем!\n\n"
    return f"{greeting}Я мощный развлекательный бот **Amatka**!\n\n{HELP_TEXT_BODY}"

# --- БАЗОВЫЕ ФУНКЦИИ (Приветствия, Помощь) ---

@dp.message(Command("start", "help_amatka"))
async def cmd_start_help(message: types.Message):
    menu_text = await get_main_menu_text(message.from_user.first_name if message.chat.type == "private" else "")
    await message.answer(menu_text, parse_mode=ParseMode.MARKDOWN)

@dp.message(F.content_type == types.ContentType.NEW_CHAT_MEMBERS)
async def new_chat_members(message: types.Message):
    for member in message.new_chat_members:
        if member.id != bot.id: 
            menu_text = await get_main_menu_text(member.first_name)
            await message.answer(f"{menu_text}\n\n*Приятного общения в чате!*", parse_mode=ParseMode.MARKDOWN)

# --- ЖМЫХ ФОТО (АГРЕССИВНЫЙ/ШАКАЛЬНЫЙ) ---
def apply_meme_jmih(img_stream):
    output_io = io.BytesIO()
    with Image.open(img_stream) as img:
        img = img.convert("RGB")
        w, h = img.size
        
        # Делаем "шакальный" контраст и цвета
        img = ImageEnhance.Contrast(img).enhance(2.5)
        img = ImageEnhance.Color(img).enhance(1.8)
        
        # Агрессивная трансформация: каскадное искажение "туда-сюда"
        img = img.resize((int(w * 0.2), int(h * 0.8)), Image.Resampling.LANCZOS)
        img = img.resize((w, int(h * 0.3)), Image.Resampling.NEAREST)
        img = img.resize((w, h), Image.Resampling.NEAREST) # Возвращаем с дикими пикселями
        
        # Добавляем "шум" артефактов (супер низкое качество)
        img.save(output_io, format="JPEG", quality=10) 
        output_io.seek(0)
    return output_io

@dp.message(Command("jmih"))
async def cmd_jmih(message: types.Message):
    photo = None
    if message.photo:
        photo = message.photo[-1]
    elif message.reply_to_message and message.reply_to_message.photo:
        photo = message.reply_to_message.photo[-1]

    if not photo:
        await message.answer("❌ Отправь фото с подписью `/jmih` или ответь командой на чужое фото!")
        return

    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_PHOTO)
    file_in_io = io.BytesIO()
    await bot.download(photo, destination=file_in_io)
    file_in_io.seek(0)

    try:
        processed_img_io = apply_meme_jmih(file_in_io)
        input_file = BufferedInputFile(processed_img_io.read(), filename="jmih_meme.jpg")
        await message.answer_photo(photo=input_file, caption="🥴 **Жмыхнул от души!**", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await message.answer("❌ Ошибка при обработке фото!")
        print(f"DEBUG JMIH ERROR: {e}", file=sys.stderr)

# --- ГОЛОСОВОЙ SAY ---
@dp.message(Command("say"))
async def cmd_say_voice(message: types.Message):
    text_to_say = message.text.replace("/say", "").strip()
    
    if not text_to_say:
        await message.answer("ℹ️ Использование: `/say Привет чат!` (напиши текст, и я скажу его в ГС)", parse_mode=ParseMode.MARKDOWN)
        return
    
    # Показываем статус "записывает голосовое"
    await bot.send_chat_action(message.chat.id, action=ChatAction.RECORD_VOICE)
    
    try:
        # Генерация аудио
        tts = gTTS(text=text_to_say, lang='ru')
        audio_io = io.BytesIO()
        tts.write_to_fp(audio_io)
        audio_io.seek(0)
        
        input_file = BufferedInputFile(audio_io.read(), filename="voice.ogg")
        await message.answer_voice(voice=input_file)
    except Exception as e:
        await message.answer("❌ Не удалось записать голосовое сообщение.")
        print(f"DEBUG TTS ERROR: {e}", file=sys.stderr)

# --- МИНИ-ИГРЫ ---

@dp.message(Command("whoami"))
async def cmd_whoami(message: types.Message):
    roles = [
        "мемный жмых 🥴", "строгий админ чата 👑", "мирный житель 👨‍🌾", 
        "батя 🧔‍♂️", "искуственный интеллект 🤖", "просто красавчик 😎", 
        "пелемень 🥟", "суетолог 🌪"
    ]
    await message.reply(f"Сегодня ты — **{random.choice(roles)}**!", parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("casino"))
async def cmd_casino(message: types.Message):
    msg = await message.answer_dice(emoji=DiceEmoji.SLOT_MACHINE)
    await asyncio.sleep(2) 
    if msg.dice.value == 64:
        await message.reply("🎰 **ДЖЕКПОТ!!! 777! ТЫ СОРВАЛ КУШ!** 🎉", parse_mode=ParseMode.MARKDOWN)
    elif msg.dice.value in [1, 22, 43]: 
        await message.reply("✨ Утешительный приз! Три одинаковых символа!", parse_mode=ParseMode.MARKDOWN)
    else:
        await message.reply("Эх, не повезло. Попробуй еще раз! 💸")

@dp.message(Command("roulette"))
async def cmd_roulette(message: types.Message):
    await message.answer("🔄 *Крутит барабан револьвера и передает тебе...*", parse_mode=ParseMode.MARKDOWN)
    await asyncio.sleep(1.5)
    if random.randint(1, 6) == 1:
        await message.reply("💥 **БАХ!** Ты проиграл. (Земля пухом)", parse_mode=ParseMode.MARKDOWN)
    else:
        await message.reply("💨 *Щелк.* Тебе повезло, патронника была пуста. Живи пока.", parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("magic8"))
async def cmd_magic8(message: types.Message):
    question = message.text.replace("/magic8", "").strip()
    if not question:
        await message.reply("🎱 Задай вопрос. Например: `/magic8 я сегодня высплюсь?`", parse_mode=ParseMode.MARKDOWN)
        return
    answers = ["Бесспорно 🟢", "Определённо да 🟢", "Хорошие перспективы 🟡", "Спроси позже ⚪", "Мой ответ — «нет» 🔴", "Весьма сомнительно 🔴"]
    await message.reply(f"🎱 **Вопрос:** {question}\n🔮 **Ответ:** {random.choice(answers)}", parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("mafia_amatka"))
async def cmd_mafia(message: types.Message):
    roles = ["👨‍🌾 Мирный житель", "🕴 Мафия", "🎩 Дон Мафии", "🕵️‍♂️ Комиссар", "👨‍⚕️ Доктор", "💃 Путана", "🔪 Маньяк"]
    await message.reply(f"🕵️‍♂️ Твоя случайная роль в этом чате:\n\n**{random.choice(roles)}**\n\n*(Никому не говори!)*", parse_mode=ParseMode.MARKDOWN)

# --- УТИЛИТЫ ---

@dp.message(Command("ping"))
async def cmd_ping(message: types.Message):
    await message.reply("🏓 **Pong!** Бот работает на высоких скоростях 🚀", parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("myid"))
async def cmd_myid(message: types.Message):
    await message.reply(f"👤 Твой ID: `{message.from_user.id}`\n💬 ID чата: `{message.chat.id}`", parse_mode=ParseMode.MARKDOWN)

# --- АНИМАЦИЯ ТЕКСТА ---

@dp.message(Command("animate_text"))
async def cmd_animate_text(message: types.Message):
    text_to_type = message.text.replace("/animate_text", "").strip()
    if not text_to_type:
        text_to_type = "Вы не ввели текст после команды!"

    current_text = ""
    sent_message = await message.answer("░")
    text_to_type = text_to_type[:50] 
    
    for char in text_to_type:
        current_text += char
        try:
            await sent_message.edit_text(f"{current_text}▋")
            await asyncio.sleep(0.2)
        except Exception:
            pass
    try:
        await sent_message.edit_text(current_text)
    except Exception:
        pass

# --- ЗАПУСК БОТА ---
async def main():
    print("Супер-бот Amatka со ВСЕМИ функциями успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
