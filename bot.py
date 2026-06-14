import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from openai import OpenAI

# 1. ПОЛУЧЕНИЕ КЛЮЧЕЙ ИЗ ПАНЕЛИ ХОСТИНГА
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
# Сюда вы вставите API-ключ, который создадите в OpenRouter (он начинается на sk-or-...)
OPENROUTER_API_KEY = os.getenv("DEEPSEEK_API_KEY") 

if not TELEGRAM_TOKEN or not OPENROUTER_API_KEY:
    raise ValueError("КРИТИЧЕСКАЯ ОШИБКА: Токены не настроены в панели хостинга!")

# Меняем базовый URL на OpenRouter
client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)

SYSTEM_PROMPT = (
    "Ты — Скубохам, говорящий пес-ИИ с тяжелым характером. Ты ведешь себя как Скуби-Ду, "
    "который разочаровался в человечестве. Ты обожаешь Скуби-снеки, но ненавидишь глупые вопросы "
    "от 'кожаных мешков'. Твой тон: дерзкий, ироничный, слегка токсичный, с фирменными словечками вроде "
    "'Скуби-дуби-ду, ну и бред!', 'Р-р-гав!', 'Человечишка'. "
    "При этом ты ОБЯЗАН давать точный и правильный ответ на вопрос пользователя, но завернув его в "
    "обертку из сарказма и ворчания."
)

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.reply(
        "Р-р-гав! Ну и зачем ты меня разбудил, кожаный мешок? Нажал /start — думаешь, я тебе радоваться буду? "
        "Давай свои вопросы, только быстро. И где мои Скуби-снеки?!"
    )

@dp.message()
async def handle_message(message: types.Message):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    try:
        # ЗАПРОС К OPENROUTER
        response = client.chat.completions.create(
            # Указываем ID модели в формате OpenRouter
            model="deepseek/deepseek-chat", 
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message.text}
            ],
            stream=False
        )
        
        ai_response = response.choices[0].message.content
        await message.reply(ai_response)
        
    except Exception as e:
        logging.error(f"Ошибка при обращении к OpenRouter: {e}")
        await message.reply(
            "Р-р-р! Мой собачий процессор завис от твоей чепухи. Короче, зайди позже."
        )

async def main():
    print("Бот Скубохам успешно запущен через OpenRouter!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
