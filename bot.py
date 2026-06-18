import os
import asyncio
import re
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import yt_dlp
import logging

logging.basicConfig(level=logging.INFO)

TOKEN = "8868388327:AAFuR-w-jIKwG57g6B6oJQd0_stBcZrQKGI"
bot = Bot(token=TOKEN)
dp = Dispatcher()

if not os.path.exists("downloads"):
    os.makedirs("downloads")

class EditorStates(StatesGroup):
    entering_circle_time = State()

# --- ФУНКЦИИ СКАЧИВАНИЯ ---
def download_media(url: str, user_id: int, audio_only=False):
    outtmpl = f"downloads/{user_id}_raw.%(ext)s"
    
    # Добавляем impersonate для обхода защиты TikTok
    ydl_opts = {
        'outtmpl': outtmpl,
        'quiet': True,
        'impersonate': 'chrome'
    }
    
    if audio_only:
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
    else:
        ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        ydl_opts['merge_output_format'] = 'mp4'

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if audio_only:
            return os.path.splitext(filename)[0] + ".mp3"
        return os.path.splitext(filename)[0] + ".mp4"

# --- ФУНКЦИИ FFMPEG (ВИДЕО) ---
async def run_ffmpeg(cmd):
    process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    await process.communicate()
    return process.returncode == 0

async def convert_to_blur_circle(input_path, output_path, start_time="00:00"):
    filter_complex = (
        "[0:v]scale=480:480:force_original_aspect_ratio=increase,boxblur=20:10[bg];"
        "[0:v]scale=480:480:force_original_aspect_ratio=decrease[fg];"
        "[bg][fg]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2"
    )
    cmd = ['ffmpeg', '-y', '-ss', start_time, '-i', input_path, '-filter_complex', filter_complex, '-t', '60', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '64k', output_path]
    return await run_ffmpeg(cmd)

async def convert_to_crop_circle(input_path, output_path, start_time="00:00"):
    cmd = ['ffmpeg', '-y', '-ss', start_time, '-i', input_path, '-vf', "crop='min(iw,ih):min(iw,ih)',scale=480:480", '-t', '60', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '64k', output_path]
    return await run_ffmpeg(cmd)

async def convert_to_mirror(input_path, output_path):
    cmd = ['ffmpeg', '-y', '-i', input_path, '-vf', 'hflip', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'copy', output_path]
    return await run_ffmpeg(cmd)

# --- ФУНКЦИИ FFMPEG (АУДИО) ---
async def convert_audio_bass(input_path, output_path):
    cmd = ['ffmpeg', '-y', '-i', input_path, '-af', 'equalizer=f=60:width_type=h:width=50:g=15', '-vn', '-c:a', 'libmp3lame', '-q:a', '2', output_path]
    return await run_ffmpeg(cmd)

async def convert_audio_8d(input_path, output_path):
    cmd = ['ffmpeg', '-y', '-i', input_path, '-af', 'apulsator=hz=0.12', '-vn', '-c:a', 'libmp3lame', '-q:a', '2', output_path]
    return await run_ffmpeg(cmd)

# --- ХЭНДЛЕРЫ ---
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("👋 **Привет! Я твоя медиа-студия.**\nОтправь мне ссылку на TikTok, YouTube или Pinterest.")

@dp.message(F.text.regexp(r'(https?://[^\s]+)'))
async def handle_link(message: Message, state: FSMContext):
    url = message.text
    await state.update_data(video_url=url)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎬 Скачать MP4", callback_data="base_video"),
            InlineKeyboardButton(text="🎵 Вырезать MP3", callback_data="base_audio")
        ],
        [
            InlineKeyboardButton(text="✂️ Кружок (Кроп)", callback_data="circle_crop"),
            InlineKeyboardButton(text="👁 Кружок (Blur)", callback_data="circle_blur")
        ],
        [
            InlineKeyboardButton(text="🔊 Bass Boost", callback_data="audio_bass"),
            InlineKeyboardButton(text="🎧 Эффект 8D", callback_data="audio_8d")
        ],
        [
            InlineKeyboardButton(text="🪞 Отзеркалить видео", callback_data="mirror_video")
        ]
    ])
    await message.answer("⚙️ Выбери инструмент:", reply_markup=keyboard)

# 1. ОБРАБОТКА БАЗОВЫХ СКАЧИВАНИЙ
@dp.callback_query(F.data.in_(["base_video", "base_audio"]))
async def process_base(callback: CallbackQuery, state: FSMContext):
    mode = callback.data.split("_")[1] # video или audio
    user_data = await state.get_data()
    url = user_data.get('video_url')
    user_id = callback.from_user.id
    
    if not url: return await callback.answer("Ссылка устарела, отправь заново.")
    await callback.answer()
    
    status = await callback.message.answer("📥 Скачиваю оригинал...")
    raw_file = None
    try:
        if mode == "video":
            raw_file = await asyncio.to_thread(download_media, url, user_id, audio_only=False)
            await status.edit_text("🚀 Отправляю видео...")
            await callback.message.answer_video(video=FSInputFile(raw_file))
        else:
            raw_file = await asyncio.to_thread(download_media, url, user_id, audio_only=True)
            await status.edit_text("🚀 Отправляю аудио...")
            await callback.message.answer_audio(audio=FSInputFile(raw_file))
    except Exception as e:
        logging.error(f"Error base: {e}")
        await status.edit_text("❌ Ошибка при скачивании.")
    finally:
        await status.delete()
        if raw_file and os.path.exists(raw_file): os.remove(raw_file)

# 2. ОБРАБОТКА КРУЖКОВ (Запрос времени)
@dp.callback_query(F.data.in_(["circle_crop", "circle_blur"]))
async def process_circle_start(callback: CallbackQuery, state: FSMContext):
    circle_type = callback.data.split("_")[1]
    await state.update_data(circle_type=circle_type)
    await callback.answer()
    await state.set_state(EditorStates.entering_circle_time)
    await callback.message.answer("⏱ Напиши таймкод начала кружка в формате `минуты:секунды` (например, `00:15` или `01:20`).\nДля старта с начала пришли `0`.", parse_mode="Markdown")

# 3. ГЕНЕРАЦИЯ КРУЖКОВ (После ввода времени)
@dp.message(EditorStates.entering_circle_time)
async def process_circle_finish(message: Message, state: FSMContext):
    time_input = message.text.strip()
    if time_input == "0": start_time = "00:00:00"
    elif re.match(r'^\d{2}:\d{2}$', time_input): start_time = f"00:{time_input}"
    else: return await message.answer("❌ Неверный формат. Пример: `00:10` или `0`.")

    user_data = await state.get_data()
    url = user_data['video_url']
    circle_type = user_data['circle_type']
    user_id = message.from_user.id
    
    await state.clear()
    status = await message.answer("⏳ Создаю кружок...")
    raw_file, out_file = None, f"downloads/{user_id}_circle.mp4"
    
    try:
        raw_file = await asyncio.to_thread(download_media, url, user_id, audio_only=False)
        success = await convert_to_blur_circle(raw_file, out_file, start_time) if circle_type == "blur" else await convert_to_crop_circle(raw_file, out_file, start_time)
        
        if success:
            await status.edit_text("🚀 Отправляю кружок...")
            await message.answer_video_note(video_note=FSInputFile(out_file))
        else:
            raise Exception("FFmpeg circle error")
    except Exception as e:
        logging.error(f"Error circle: {e}")
        await message.answer("❌ Ошибка обработки кружка.")
    finally:
        await status.delete()
        for f in [raw_file, out_file]:
            if f and os.path.exists(f): os.remove(f)

# 4. ОБРАБОТКА АУДИО ЭФФЕКТОВ И ЗЕРКАЛА
@dp.callback_query(F.data.in_(["audio_bass", "audio_8d", "mirror_video"]))
async def process_effects(callback: CallbackQuery, state: FSMContext):
    action = callback.data
    user_data = await state.get_data()
    url = user_data.get('video_url')
    user_id = callback.from_user.id
    
    if not url: return await callback.answer("Ссылка устарела, отправь заново.")
    await callback.answer()
    
    status = await callback.message.answer("🪄 Накладываю эффекты, подожди...")
    raw_file, out_file = None, f"downloads/{user_id}_effect.mp4"
    
    try:
        if action == "mirror_video":
            raw_file = await asyncio.to_thread(download_media, url, user_id, audio_only=False)
            success = await convert_to_mirror(raw_file, out_file)
            if success:
                await status.edit_text("🚀 Отправляю...")
                await callback.message.answer_video(video=FSInputFile(out_file), caption="🪞 Отзеркалено!")
                
        else: # Аудио эффекты
            out_file = f"downloads/{user_id}_effect.mp3"
            raw_file = await asyncio.to_thread(download_media, url, user_id, audio_only=True)
            success = await convert_audio_bass(raw_file, out_file) if action == "audio_bass" else await convert_audio_8d(raw_file, out_file)
            if success:
                await status.edit_text("🚀 Отправляю...")
                await callback.message.answer_audio(audio=FSInputFile(out_file), caption="🔊 Эффект наложен!")

        if not success: raise Exception("FFmpeg effect error")
            
    except Exception as e:
        logging.error(f"Error effect: {e}")
        await status.edit_text("❌ Ошибка при наложении эффекта.")
    finally:
        await status.delete()
        for f in [raw_file, out_file]:
            if f and os.path.exists(f): os.remove(f)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
