import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import CommandStart
import yt_dlp
import logging

logging.basicConfig(level=logging.INFO)

TOKEN = "8868388327:AAFuR-w-jIKwG57g6B6oJQd0_stBcZrQKGI"
bot = Bot(token=TOKEN)
dp = Dispatcher()

if not os.path.exists("downloads"):
    os.makedirs("downloads")

# Базовая функция скачивания исходника
def download_media(url: str, user_id: int):
    outtmpl = f"downloads/{user_id}_raw.%(ext)s"
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': outtmpl,
        'merge_output_format': 'mp4',
        'quiet': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        return os.path.splitext(filename)[0] + ".mp4"

# Функция FFmpeg: Создание кружка (Квадрат 480х480, макс 60 сек, кодеки H.264/AAC)
async def convert_to_circle(input_path, output_path):
    cmd = [
        'ffmpeg', '-y', '-i', input_path,
        '-vf', "crop='min(iw,ih):min(iw,ih)',scale=480:480",
        '-t', '60',
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-b:a', '64k',
        output_path
    ]
    process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    await process.communicate()
    return process.returncode == 0

# Функция FFmpeg: Зеркальное отражение видео
async def convert_to_mirror(input_path, output_path):
    cmd = [
        'ffmpeg', '-y', '-i', input_path,
        '-vf', 'hflip',
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
        '-c:a', 'copy',
        output_path
    ]
    process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    await process.communicate()
    return process.returncode == 0

# Функция FFmpeg: Извлечение MP3
async def convert_to_mp3(input_path, output_path):
    cmd = [
        'ffmpeg', '-y', '-i', input_path,
        '-vn', '-c:a', 'libmp3lame', '-q:a', '4',
        output_path
    ]
    process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    await process.communicate()
    return process.returncode == 0


@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "👋 **Привет! Я твоя карманная медиа-студия.**\n\n"
        "Отправь мне ссылку на видео (TikTok, YouTube, Pinterest), и выбери инструмент монтажа!",
        parse_mode="Markdown"
    )

@dp.message(F.text.regexp(r'(https?://[^\s]+)'))
async def handle_link(message: Message):
    url = message.text
    
    # Кнопки управления контентом
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎬 Скачать MP4", callback_data=f"mode_video__{url}"),
            InlineKeyboardButton(text="🎵 Вырезать MP3", callback_data=f"mode_audio__{url}")
        ],
        [
            InlineKeyboardButton(text="🔄 Сделать КРУЖОК", callback_data=f"mode_circle__{url}"),
            InlineKeyboardButton(text="🪞 Отзеркалить", callback_data=f"mode_mirror__{url}")
        ]
    ])
    
    await message.answer("🛠 Что делаем с этим контентом?", reply_markup=keyboard)


@dp.callback_query(F.data.startswith("mode_"))
async def process_media(callback: CallbackQuery):
    data_split = callback.data.split("__")
    mode = data_split[0].split("_")[1]  # video, audio, circle, mirror
    url = data_split[1]
    user_id = callback.from_user.id
    
    await callback.answer()
    status_msg = await callback.message.answer("📥 Скачиваю исходник с платформы...")

    raw_file = None
    out_file = None

    try:
        # Step 1: Качаем чистый исходник во временный файл
        raw_file = await asyncio.to_thread(download_media, url, user_id)
        
        # Step 2: Обработка в зависимости от выбранного режима
        if mode == "video":
            await status_msg.edit_text("🚀 Файл готов! Отправляю...")
            await callback.message.answer_video(video=FSInputFile(raw_file), caption="Твой исходник! 🎬")
            
        elif mode == "audio":
            await status_msg.edit_text("✂️ Вырезаю аудиодорожку...")
            out_file = f"downloads/{user_id}_audio.mp3"
            if await convert_to_mp3(raw_file, out_file):
                await status_msg.edit_text("🚀 Отправляю аудио...")
                await callback.message.answer_audio(audio=FSInputFile(out_file), caption="Музыка для твоего тренда! 🎵")
            else:
                raise Exception("FFmpeg audio error")
                
        elif mode == "circle":
            await status_msg.edit_text("📐 Кропаю в квадрат и сжимаю для кружка...")
            out_file = f"downloads/{user_id}_circle.mp4"
            if await convert_to_circle(raw_file, out_file):
                await status_msg.edit_text("🚀 Отправляю кружок...")
                await callback.message.answer_video_note(video_note=FSInputFile(out_file))
            else:
                raise Exception("FFmpeg circle error")
                
        elif mode == "mirror":
            await status_msg.edit_text("🪞 Отзеркаливаю видео для обхода алгоритмов...")
            out_file = f"downloads/{user_id}_mirror.mp4"
            if await convert_to_mirror(raw_file, out_file):
                await status_msg.edit_text("🚀 Отправляю уникализированное видео...")
                await callback.message.answer_video(video=FSInputFile(out_file), caption="Видео успешно отзеркалено! Удачи в рекомендациях 😉")
            else:
                raise Exception("FFmpeg mirror error")

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await status_msg.edit_text("❌ Произошла ошибка при обработке файла. Проверь ссылку или попробуй позже.")
        
    finally:
        # Чистим за собой мусор на хостинге, чтобы диск не переполнился
        await status_msg.delete()
        for file in [raw_file, out_file]:
            if file and os.path.exists(file):
                os.remove(file)

async def main():
    print("MediaForge запущен с поддержкой кружков и уникализации!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
