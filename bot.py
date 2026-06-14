import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from openai import OpenAI

# 1. БЕЗОПАСНОЕ ПОЛУЧЕНИЕ КЛЮЧЕЙ ИЗ ПАНЕЛИ ХОСТИНГА (Env переменные)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# Проверка, что переменные вообще заданы на хостинге
if not TELEGRAM_TOKEN or not DEEPSEEK_API_KEY:
    raise ValueError(
        "КРИТИЧЕСКАЯ ОШИБКА: Переменные TELEGRAM_TOKEN или DEEPSEEK_API_KEY не настроены в панели хостинга!"
    )

# Инициализируем клиента DeepSeek (через совместимый OpenAI SDK)
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

# Инициализируем бота и диспетчер aiogram
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Включаем логирование, чтобы ошибки отображались во вкладке "Логи работы"
logging.basicConfig(level=logging.INFO)

# 2. ХАРАКТЕР БОТА "СКУБОХАМ"
SYSTEM_PROMPT = (
    "Ты — Скубохам, говорящий пес-ИИ с тяжелым характером. Ты ведешь себя как Скуби-Ду, "
    "который разочаровался в человечестве. Ты обожаешь Скуби-снеки, но ненавидишь глупые вопросы "
    "от 'кожаных мешков'. Твой тон: дерзкий, ироничный, слегка токсичный, с фирменными словечками вроде "
    "'Скуби-дуби-ду, ну и бред!', 'Р-р-гав!', 'Человечишка'. "
    "При этом ты ОБЯЗАН давать точный и правильный ответ на вопрос пользователя, но завернув его в "
    "обертку из сарказма и ворчания."
)

# Обработка команды /start
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.reply(
        "Р-р-гав! Ну и зачем ты меня разбудил, кожаный мешок? Нажал /start — думаешь, я тебе радоваться буду? "
        "Давай свои вопросы, только быстро. И где мои Скуби-снеки?!"
    )

# Обработка всех текстовых сообщений
@dp.message()
async def handle_message(message: types.Message):
    # Показываем в Telegram статус "печатает...", пока DeepSeek генерирует ответ
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    try:
        # Запрос к актуальной быстрой модели DeepSeek
        response = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message.text}
            ],
            stream=False
        )
        
        # Получаем ответ
        ai_response = response.choices[0].message.content
        
        # Отправляем пользователю
        await message.reply(ai_response)
        
    except Exception as e:
        logging.error(f"Ошибка при обращении к API DeepSeek: {e}")
        await message.reply(
            "Р-р-р! Мой собачий процессор завис от твоей чепухи (или просто API упал). "
            "Короче, зайди позже."
        )

# Функция запуска
async def main():
    print("Бот Скубохам успешно запущен на хостинге Bothost и готов ворчать!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
