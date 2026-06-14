import os
import asyncio
import sys
import io
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ChatAction, ParseMode, DiceEmoji
from aiogram.types import BufferedInputFile
from PIL import Image, ImageEnhance, ImageOps
from gtts import gTTS

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- МЕМНЫЙ ЖМЫХ (Имитация warp) ---
def apply_meme_jmih(img_stream):
    output_io = io.BytesIO()
    with Image.open(img_stream) as img:
        img = img.convert("RGB")
        w, h = img.size
        
        # Делаем "шакальный" контраст
        img = ImageEnhance.Contrast(img).enhance(2.0)
        img = ImageEnhance.Color(img).enhance(1.5)
        
        # Агрессивная трансформация: каскадное искажение
        # Сжимаем по X, расширяем по Y, пикселизуем
        img = img.resize((int(w * 0.2), int(h * 0.8)), Image.Resampling.LANCZOS)
        img = img.resize((w, h), Image.Resampling.NEAREST)
        
        # Добавляем "шум" артефактов
        img.save(output_io, format="JPEG", quality=10) 
        output_io.seek(0)
    return output_io

# --- ГОЛОСОВОЙ SAY ---
@dp.message(Command("say"))
async def cmd_say_voice(message: types.Message):
    text = message.text.replace("/say", "").strip()
    if not text:
        await message.answer("Напиши текст, который я должен озвучить!")
        return
    
    await bot.send_chat_action(message.chat.id, action=ChatAction.RECORD_VOICE)
    
    # Генерация аудио
    tts = gTTS(text=text, lang='ru')
    audio_io = io.BytesIO()
    tts.write_to_fp(audio_io)
    audio_io.seek(0)
    
    await message.answer_voice(voice=BufferedInputFile(audio_io.read(), filename="voice.ogg"))

# --- НОВАЯ МИНИ-ИГРА: РЕЙТИНГ "КТО ТЫ СЕГОДНЯ?" ---
@dp.message(Command("whoami"))
async def cmd_whoami(message: types.Message):
    roles = ["мемный жмых", "админ чата", "мирный житель", "батя", "нейросеть", "красавчик"]
    await message.reply(f"Сегодня ты — *{random.choice(roles)}*!", parse_mode=ParseMode.MARKDOWN)

# --- ИНТЕГРАЦИЯ С ТВОИМИ РЕФЕРЕНСАМИ ---
# Теперь jmih будет максимально приближен к "шакальному" стилю, как в 193141.jpg и 193140.jpg
@dp.message(Command("jmih"))
async def cmd_jmih(message: types.Message):
    photo = message.photo[-1] if message.photo else (message.reply_to_message.photo[-1] if message.reply_to_message and message.reply_to_message.photo else None)
    
    if not photo:
        await message.answer("Отправь фото или ответь командой на фото!")
        return

    await bot.send_chat_action(message.chat.id, action=ChatAction.UPLOAD_PHOTO)
    file_in_io = io.BytesIO()
    await bot.download(photo, destination=file_in_io)
    file_in_io.seek(0)
    
    processed = apply_meme_jmih(file_in_io)
    await message.answer_photo(photo=BufferedInputFile(processed.read(), filename="jmih.jpg"), caption="Жмыхнул по полной! 🥴")

# --- ЗАПУСК ---
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
