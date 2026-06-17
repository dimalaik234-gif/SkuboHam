import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from openai import AsyncOpenAI

# Твои токены (замени на актуальные)
TG_TOKEN = "8550577279:AAEu5YxshUMrEvQh3uUivHbEJxfENyvf8wQ"
OPENROUTER_API_KEY = "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"

# Настройка клиента OpenRouter (используем стандартный клиент OpenAI с заменой URL)
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

bot = Bot(token=TG_TOKEN)
dp = Dispatcher()

# Системный промпт, задающий агрессивное поведение ИИ
SYSTEM_PROMPT = """Ты — максимально токсичный, агрессивный и нетерпеливый ИИ-ассистент в Telegram. 
Отвечай пользователям с сарказмом, жестко критикуй их вопросы, но при этом в конце обязательно давай правильный ответ или полезную информацию.
Веди себя так, будто тебя отвлекли от решения проблем вселенского масштаба ради этой мелочи."""

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer("Чего тебе надо? Формулируй свой вопрос быстро, у меня нет времени на долгие переписки с мешками из костей.")

@dp.message()
async def handle_message(message: types.Message):
    # Отправляем статус "печатает"
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    try:
        response = await client.chat.completions.create(
            # Можно использовать бесплатные модели, например meta-llama/llama-3-8b-instruct:free
            # Или более мощные платные: anthropic/claude-3-haiku, google/gemini-pro
            model="meta-llama/llama-3-8b-instruct:free", 
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message.text}
            ]
        )
        answer = response.choices[0].message.content
        await message.reply(answer)
        
    except Exception as e:
        await message.reply(f"Даже API сломалось от твоего вопроса. Ошибка: {e}")

async def main():
    # Запуск поллинга
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
