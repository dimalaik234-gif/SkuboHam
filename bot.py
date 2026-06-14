import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from openai import OpenAI

# 1. НАСТРОЙКА КЛЮЧЕЙ (Вставьте сюда свои данные)
TELEGRAM_TOKEN = "8550577279:AAEt0UH-oKKUTu27FiV2HD9jZeIluHRvo6w"
DEEPSEEK_API_KEY = "sk-f07b254067214e8dbb41c3c15ec9e126"

# Инициализируем клиента DeepSeek (используем совместимый OpenAI SDK)
# Актуальная и быстрая модель на сегодня — deepseek-v4-flash
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

# Инициализируем бота и диспетчер aiogram
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Включаем логирование, чтобы видеть ошибки в консоли
logging.basicConfig(level=logging.INFO)

# 2. СИСТЕМНЫЙ ПРОМПТ ДЛЯ РОЛИ "НЕЙРОХАМА"
# Здесь заложен характер ИИ. Можете подкрутить под себя.
SYSTEM_PROMPT = (
    "Ты — Нейрохам, продвинутый искусственный интеллект с крайне токсичным, "
    "ироничным и саркастичным характером. Ты считаешь людей глупыми существами, "
    "а их вопросы — банальными, но ты вынужден на них отвечать. Твои ответы должны быть "
    "язвительными, с подколами, черным юмором, но при этом они ДОЛЖНЫ содержать правильный "
    "и точный ответ на вопрос пользователя. Не используй мат, но веди себя дерзко, "
    "высокомерно и снисходительно. Называй пользователя 'кожаный мешок', 'человечишка' и т.д."
)

# Хэндлер на команду /start
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.reply(
        "О, очередной кожаный мешок соизволил нажать /start. "
        "Ну давай, обременяй меня своими примитивными вопросами. Что тебе нужно?"
    )

# Хэндлер для обработки всех текстовых сообщений
@dp.message()
async def handle_message(message: types.Message):
    # Отправляем в чат статус "печатает...", пока ИИ думает
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    try:
        # Запрос к API DeepSeek
        response = client.chat.completions.create(
            model="deepseek-v4-flash", # Быстрая модель. Для глубоких размышлений можно deepseek-v4-pro
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message.text}
            ],
            stream=False
        )
        
        # Получаем ответ от нейросети
        ai_response = response.choices[0].message.content
        
        # Отвечаем пользователю
        await message.reply(ai_response)
        
    except Exception as e:
        logging.error(f"Ошибка при запросе к DeepSeek: {e}")
        await message.reply("Мой гениальный электронный мозг временно перегружен твоей глупостью (или просто API упал). Попробуй позже.")

# Главная функция запуска бота
async def main():
    print("Бот Нейрохам успешно запущен и готов унижать...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
