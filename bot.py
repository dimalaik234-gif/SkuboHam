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

# Состояния для FSM (интерактивного диалога)
class EditorStates(StatesGroup):
    choosing_action = State()
    entering_circle_time = State()

# Скачивание исходника
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

# FFmpeg: Кружок с размытыми краями (чтобы не терять бока видео) и обрезкой по времени
async def convert_to_blur_circle(input_path, output_path, start_time="00:00"):
    # Фильтр ffmpeg: делает копию видео, размывает её в фон, сверху накладывает оригинал, вписанный в квадрат
    filter_complex = (
        "[0:v]scale=480:480:force_original_aspect_ratio=increase,boxblur=20:10[bg];"
        "[0:v]scale=480:480:force_original_aspect_ratio=decrease[fg];"
        "[bg][fg]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2"
    )
    cmd = [
        'ffmpeg', '-y', '-ss', start_time, '-i', input_path,
        '-filter_complex', filter_complex,
        '-t', '60',  # Максимум 1 минута для кружка
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-b:a', '64k',
        output_path
    ]
    process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    await process.communicate()
    return process.returncode == 0

# FFmpeg: Обычный кружок (кроп по центру) с обрезкой времени
async def convert_to_crop_circle(input_path, output_path, start_time="00:00"):
    cmd = [
        'ffmpeg', '-y', '-ss', start_time, '-i', input_path,
        '-vf', "crop='min(iw,ih):min(iw,ih)',scale=480:480",
        '-t', '60',
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-b:a', '64k',
        output_path
    ]
    process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    await process.communicate()
    return process.returncode == 0

# FFmpeg: Аудиоэффект Bass Boost
async def convert_audio_bass(input_path, output_path):
    cmd = [
        'ffmpeg', '-y', '-i', input_path,
        '-af', 'equalizer=f=60:width_type=h:width=50:g=12', # Усиление частоты 60Гц на 12дБ
        '-vn', '-c:a', 'libmp3lame', '-q:a', '2',
        output_path
    ]
    process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    await process.communicate()
    return process.returncode == 0

# FFmpeg: Аудиоэффект 8D (панорамирование звука влево-вправо по синусоиде)
async def convert_audio_8d(input_path, output_path):
    cmd = [
        'ffmpeg', '-y', '-i', input_path,
        '-af', 'apulsator=hz=0.12', # Звук плавно гуляет между ушами с частотой 0.12 Гц
        '-vn', '-c:a', 'libmp3lame', '-q:a', '2',
        output_path
    ]
    process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    await process.communicate()
    return process.returncode == 0


@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "👋 **Добро пожаловать в MediaForge Studio!**\n\n"
        "Отправь мне ссылку на видео (TikTok, YouTube, Pinterest), и мы создадим шедевр.",
        parse_mode="Markdown"
    )

@dp.message(F.text.regexp(r'(https?://[^\s]+)'))
async def handle_link(message: Message, state: FSMContext):
    url = message.text
    await state.update_data(video_url=url) # Сохраняем ссылку в память бота
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎬 Обычный кружок (Кроп)", callback_data="btn_circle_crop"),
            InlineKeyboardButton(text="👁 Кружок с Blur-фоном", callback_data="btn_circle_blur")
        ],
        [
            InlineKeyboardButton(text="🔊 Музыка: Bass Boost", callback_data="btn_audio_bass"),
            InlineKeyboardButton(text="🎧 Музыка: Эффект 8D", callback_data="btn_audio_8d")
        ],
        [
            InlineKeyboardButton(text="🪞 Отзеркалить MP4", callback_data="btn_mirror")
        ]
    ])
    
    await message.answer("⚙️ **Панель редактирования.** Выберите режим обработки контента:", reply_markup=keyboard, parse_mode="Markdown")

# Обработка выбора режимов для КРУЖКОВ
@dp.callback_query(F.data.startswith("btn_circle_"))
async def choose_circle_type(callback: CallbackQuery, state: FSMContext):
    circle_type = callback.data.split("_")[2] # crop или blur
    await state.update_data(circle_type=circle_type)
    
    await callback.answer()
    await state.set_state(EditorStates.entering_circle_time)
    
    await callback.message.answer(
        "⏱ **С какого момента начать кружок?**\n\n"
        "Напишите таймкод в формате `минуты:секунды` (например, `00:15` или `01:20`).\n"
        "Если хотите начать с самого начала, просто пришлите `0`.",
        parse_mode="Markdown"
    )

# Принятие таймкода и старт обработки кружка
@dp.message(EditorStates.entering_circle_time)
async def process_circle_generation(message: Message, state: FSMContext):
    time_input = message.text.strip()
    
    # Валидация времени
    if time_input == "0":
        start_time = "00:00:00"
    elif re.match(r'^\d{2}:\d{2}$', time_input):
        start_time = f"00:{time_input}"
    else:
        await message.answer("❌ Неверный формат. Напишите, например, `00:10` (для 10-й секунды) или `0` для старта с начала.")
        return

    user_data = await state.get_data()
    url = user_data['video_url']
    circle_type = user_data['circle_type']
    user_id = message.from_user.id
    
    await state.clear() # Сбрасываем состояние
    status_msg = await message.answer("⏳ Скачиваю видео и магиирую над кружком...")
    
    raw_file = None
    out_file = f"downloads/{user_id}_circle_final.mp4"
    
    try:
        raw_file = await asyncio.to_thread(download_media, url, user_id)
        
        if circle_type == "blur":
            success = await convert_to_blur_circle(raw_file, out_file, start_time)
        else:
            success = await convert_to_crop_circle(raw_file, out_file, start_time)
            
        if success:
            await status_msg.edit_text("🚀 Отправляю кружок...")
            await message.answer_video_note(video_note=FSInputFile(out_file))
        else:
            raise Exception("FFmpeg processing failed")
            
    except Exception as e:
        logging.error(f"Error: {e}")
        await message.answer("❌ Не удалось создать кружок. Проверьте длину видео или таймкод.")
    finally:
        await status_msg.delete()
        for f in [raw_file, out_file]:
            if f and os.path.exists(f): os.remove(f)

# Обработка звуковых эффектов (Bass Boost / 8D)
@dp.callback_query(F.data.startswith("btn_audio_"))
async def process_audio_effects(callback: CallbackQuery, state: FSMContext):
    effect = callback.data.split("_")[2] # bass или 8d
    user_data = await state.get_data()
    url = user_data.get('video_url')
    user_id = callback.from_user.id
    
    if not url:
        await callback.answer("Ошибка: сессия истекла. Отправьте ссылку заново.", show_alert=True)
        return
        
    await callback.answer()
    status_msg = await callback.message.answer(f"🎵 Извлекаю аудио и накладываю эффект {effect.upper()}...")
    
    raw_file = None
    out_file = f"downloads/{user_id}_{effect}.mp3"
    
    try:
        raw_file = await asyncio.to_thread(download_media, url, user_id)
        
        if effect == "bass":
            success = await convert_audio_bass(raw_file, out_file)
            caption = "🔊 Трек с мощным Bass Boost готов для твоего монтажа!"
        else:
            success = await convert_audio_8d(raw_file, out_file)
            caption = "🎧 8D трек готов! Слушай в наушниках."
            
        if success:
            await status_msg.edit_text("🚀 Отправляю аудио...")
            await callback.message.answer_audio(audio=FSInputFile(out_file), caption=caption)
        else:
            raise Exception("FFmpeg audio processing failed")
            
    except Exception as e:
        logging.error(f"Error: {e}")
        await callback.message.answer("❌ Не удалось обработать аудиодорожку.")
    finally:
        await status_msg.delete()
        await state.clear()
        for f in [raw_file, out_file]:
            if f and os.path.exists(f): os.remove(f)

# (Остальной код зеркалирования из предыдущего шага можно оставить по аналогии)
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
