import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart

# Твои токены
TG_TOKEN = "8550577279:AAFz0GKDzblPFwMROagx0JezVl16VqlYDUg"
OPENROUTER_API_KEY = "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"

bot = Bot(token=TG_TOKEN)
dp = Dispatcher()

# Системный промпт для агрессивного ИИ
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
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "nvidia/nemotron-3-ultra-550b-a55b:free", 
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message.text}
        ]
    }
    
    try:
        # Отправляем прямой POST-запрос к OpenRouter
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    answer = data['choices'][0]['message']['content']
                    await message.reply(answer)
                else:
                    error_text = await response.text()
                    await message.reply(f"Нейросеть выдала ошибку {response.status}. Кажется, ты её сломал своим присутствием.")
                    
    except Exception as e:
        await message.reply(f"Даже сервер не выдержал твоего сообщения. Ошибка: {e}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
