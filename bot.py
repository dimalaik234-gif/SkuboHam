import os
import asyncio
import sys
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Bothost передаст токен через переменные окружения.
# Мы берем переменную с именем BOT_TOKEN. Если её нет — бот выдаст ошибку при запуске.
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    print("Ошибка: Переменная окружения BOT_TOKEN не задана!", file=sys.stderr)
    sys.exit(1)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# 1. Анимация "Печатающийся текст"
@dp.message(Command("animate_text"))
async def cmd_animate_text(message: types.Message):
    text_to_type = "Привет! Я живой анимированный бот... 🚀"
    current_text = ""
    sent_message = await message.answer("░")
    
    for char in text_to_type:
        current_text += char
        await sent_message.edit_text(f"{current_text}▋")
        # Для Bothost оставляем безопасную задержку 0.2 сек, чтобы не поймать бан от TG
        await asyncio.sleep(0.2)
        
    await sent_message.edit_text(current_text)

# 2. Анимация "Загрузка"
@dp.message(Command("loading"))
async def cmd_loading(message: types.Message):
    frames = [
        "⏳ Загрузка системы [⬜⬜⬜⬜⬜] 0%",
        "⏳ Загрузка системы [🟩⬜⬜⬜⬜] 20%",
        "⏳ Загрузка системы [🟩🟩⬜⬜⬜] 40%",
        "⏳ Загрузка системы [🟩🟩🟩⬜⬜] 60%",
        "⏳ Загрузка системы [🟩🟩🟩🟩⬜] 80%",
        "✅ Системы запущены! [🟩🟩🟩🟩🟩] 100%"
    ]
    
    sent_message = await message.answer(frames[0])
    for frame in frames[1:]:
        await asyncio.sleep(0.6)
        await sent_message.edit_text(frame)

async def main():
    print("Бот успешно запущен на Bothost!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
