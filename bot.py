import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import CommandStart
import yt_dlp

# Включаем логирование, чтобы видеть ошибки в консоли хостинга
import logging
logging.basicConfig(level=logging.INFO)

TOKEN = "8868388327:AAFuR-w-jIKwG57g6B6oJQd0_stBcZrQKGI"
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Создаем папку для временных файлов, если её нет
if not os.path.exists("downloads"):
    os.makedirs("downloads")

# Функция для скачивания через yt-dlp (запускается в отдельном потоке, чтобы бот не зависал)
def download_media(url: str, mode: str, user_id: int):
    outtmpl = f"downloads/{user_id}_%(id)s.%(ext)s"
    
    if mode == "video":
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': outtmpl,
            'merge_output_format': 'mp4',
            'quiet': True
        }
    else:  # mode == "audio"
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': outtmpl,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True
        }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        
        if mode == "audio":
            filename = os.path.splitext(filename)[0] + ".mp3"
        elif not filename.endswith(".mp4"):
            # На случай, если формат изменился при склейке
            filename = os.path.splitext(filename)[0] + ".mp4"
            
        return filename

# Команда /start
@dp.message(CommandStart())
async def cmd_start(message: Message):
    welcome_text = (
        "👋 **Привет, креатор! Я MediaForge Bot.**\n\n"
        "Я помогу тебе вытащить исходники для твоего монтажа. "
        "Просто отправь мне ссылку на видео из **TikTok, Pinterest, YouTube** или Instagram.\n\n"
        "⚡️ Что я умею:\n"
        "• Скачивать видео в лучшем качестве\n"
        "• Вырезать аудиодорожку в MP3"
    )
    await message.answer(welcome_text, parse_mode="Markdown")

# Хэндлер на получение ссылок
@dp.message(F.text.regexp(r'(https?://[^\s]+)'))
async def handle_link(message: Message):
    url = message.text
    
    # Создаем инлайн-кнопки для выбора действия
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎬 Скачать Видео", callback_data=f"dl_video__{url}"),
            InlineKeyboardButton(text="🎵 Вырезать MP3", callback_data=f"dl_audio__{url}")
        ],
        [
            InlineKeyboardButton(text="✂️ Сделать кружочек (Скоро)", callback_data="blur")
        ]
    ])
    
    await message.answer("🧠 Ссылка принята! Что делаем с этим медиа?", reply_markup=keyboard)

# Обработка нажатий на кнопки
@dp.callback_query(F.data.startswith("dl_"))
async def process_download(callback: CallbackQuery):
    # Распаковываем данные из callback_data
    data_split = callback.data.split("__")
    mode = data_split[0].split("_")[1] # video или audio
    url = data_split[1]
    
    await callback.answer()
    status_msg = await callback.message.answer("⏳ Магия началась... Скачиваю и обрабатываю файл, подожди немного.")

    try:
        # Запускаем тяжелую загрузку в фоновом потоке, чтобы бот не «умирал» для других юзеров
        file_path = await asyncio.to_thread(download_media, url, mode, callback.from_user.id)
        
        await status_msg.edit_text("🚀 Файл готов! Отправляю в Telegram...")
        
        # Отправляем файл пользователю
        telegram_file = FSInputFile(file_path)
        if mode == "video":
            await callback.message.answer_video(video=telegram_file, caption="Твой исходник готов для монтажа! 🎬")
        else:
            await callback.message.answer_audio(audio=telegram_file, caption="Звуковая дорожка извлечена! 🎵")
            
        # Удаляем файл с сервера, чтобы не забивать жесткий диск хостинга
        if os.path.exists(file_path):
            os.remove(file_path)
        await status_msg.delete()

    except Exception as e:
        logging.error(f"Ошибка при скачивании: {e}")
        await status_msg.edit_text("❌ Упс... Не удалось обработать эту ссылку. Возможно, видео приватное или сервис временно заблокировал запрос.")

# Заглушка для неактивной кнопки
@dp.callback_query(F.data == "blur")
async def process_blur(callback: CallbackQuery):
    await callback.answer("Эта фича в разработке! Скоро добавлю обрезку под формат круглых видео.", show_alert=True)

# Запуск бота
async def main():
    print("Бот успешно запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
