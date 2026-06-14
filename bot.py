import os
import asyncio
import sys
import io
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ChatAction, ParseMode, DiceEmoji
from aiogram.types import BufferedInputFile

# Для жесткого мемного жмыха
from PIL import Image, ImageEnhance, ImageOps

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    print("Ошибка: Переменная окружения BOT_TOKEN не задана!", file=sys.stderr)
    sys.exit(1)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ТЕКСТ СПРАВКИ И ПРИВЕТСТВИЯ ---
HELP_TEXT_BODY = (
    "🎮 **МИНИ-ИГРЫ:**\n"
    "🎲 `/casino` — Крутить слот-машину (выпадет ли джекпот?)\n"
    "🔫 `/roulette` — Русская рулетка (повезет или нет?)\n"
    "🎱 `/magic8 <вопрос>` — Магический шар предсказаний\n"
    "🕵️‍♂️ `/mafia_amatka` — Узнать свою случайную роль в Мафии\n\n"
    "✨ **ФИШКИ БОТА:**\n"
    "📝 `/animate_text <текст>` — Сделать живую анимацию текста\n"
    "🖼 `/jmih` (ответом на фото) — Агрессивный мемный жмых!\n"
    "🗣 `/say <текст>` — Заставить бота сказать что-то\n\n"
    "⚙️ **УТИЛИТЫ:**\n"
    "🏓 `/ping` — Проверить, работает ли бот\n"
    "🆔 `/myid` — Узнать свой Telegram ID"
)

async def get_main_menu_text(user_first_name=""):
    greeting = f"👋 Привет, {user_first_name}!\n\n" if user_first_name else "👋 Привет всем!\n\n"
    return f"{greeting}Я развлекательный бот **Amatka**!\n\n{HELP_TEXT_BODY}"

# --- БАЗОВЫЕ ФУНКЦИИ (Приветствия, Помощь) ---

@dp.message(Command("start", "help_amatka"))
async def cmd_start_help(message: types.Message):
    menu_text = await get_main_menu_text(message.from_user.first_name if message.chat.type == "private" else "")
    await message.answer(menu_text, parse_mode=ParseMode.MARKDOWN)

@dp.message(F.content_type == types.ContentType.NEW_CHAT_MEMBERS)
async def new_chat_members(message: types.Message):
    for member in message.new_chat_members:
        if member.id != bot.id: # Если добавили не самого бота
            menu_text = await get_main_menu_text(member.first_name)
            await message.answer(f"{menu_text}\n\n*Приятного общения в чате!*", parse_mode=ParseMode.MARKDOWN)

# --- НОВЫЕ МИНИ-ИГРЫ ---

@dp.message(Command("casino"))
async def cmd_casino(message: types.Message):
    """Слот-машина с проверкой выигрыша"""
    msg = await message.answer_dice(emoji=DiceEmoji.SLOT_MACHINE)
    await asyncio.sleep(2) # Ждем, пока пройдет анимация в Telegram
    
    # В Telegram значение слотов 64 означает джекпот (три семерки)
    if msg.dice.value == 64:
        await message.reply("🎰 **ДЖЕКПОТ!!! 777! ТЫ СОРВАЛ КУШ!** 🎉", parse_mode=ParseMode.MARKDOWN)
    elif msg.dice.value in [1, 22, 43]: # Три одинаковых символа (виноград, лимон, бар)
        await message.reply("✨ Утешительный приз! Три одинаковых символа!", parse_mode=ParseMode.MARKDOWN)
    else:
        await message.reply("Эх, не повезло. Попробуй еще раз! 💸")

@dp.message(Command("roulette"))
async def cmd_roulette(message: types.Message):
    """Русская рулетка (шанс 1 к 6)"""
    await message.answer("🔄 *Крутит барабан револьвера и передает тебе...*", parse_mode=ParseMode.MARKDOWN)
    await asyncio.sleep(1.5)
    
    if random.randint(1, 6) == 1:
        await message.reply("💥 **БАХ!** Ты проиграл. (Земля пухом)", parse_mode=ParseMode.MARKDOWN)
    else:
        await message.reply("💨 *Щелк.* Тебе повезло, патронника была пуста. Живи пока.", parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("magic8"))
async def cmd_magic8(message: types.Message):
    """Магический шар предсказаний"""
    question = message.text.replace("/magic8", "").strip()
    if not question:
        await message.reply("🎱 Задай вопрос после команды. Например: `/magic8 я сегодня высплюсь?`", parse_mode=ParseMode.MARKDOWN)
        return
        
    answers = [
        "Бесспорно 🟢", "Предрешено 🟢", "Определённо да 🟢", "Можешь быть уверен в этом 🟢", 
        "Вероятнее всего 🟡", "Хорошие перспективы 🟡", "Знаки говорят — «да» 🟡", 
        "Пока не ясно, попробуй снова ⚪", "Спроси позже ⚪", "Сконцентрируйся и спроси опять ⚪",
        "Даже не думай 🔴", "Мой ответ — «нет» 🔴", "По моим данным — «нет» 🔴", "Весьма сомнительно 🔴"
    ]
    await message.reply(f"🎱 **Вопрос:** {question}\n🔮 **Ответ:** {random.choice(answers)}", parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("mafia_amatka"))
async def cmd_mafia(message: types.Message):
    """Быстрая раздача ролей для оффлайн/голосовой мафии"""
    roles = [
        "👨‍🌾 Мирный житель", "👨‍🌾 Мирный житель", "👨‍🌾 Мирный житель",
        "🕴 Мафия", "🕴 Мафия", "🎩 Дон Мафии",
        "🕵️‍♂️ Комиссар", "👨‍⚕️ Доктор", "💃 Путана", "🔪 Маньяк"
    ]
    role = random.choice(roles)
    await message.reply(
        f"🕵️‍♂️ Твоя случайная роль в этом чате:\n\n**{role}**\n\n"
        f"*(Никому не говори, кто ты!)*", 
        parse_mode=ParseMode.MARKDOWN
    )

# --- УТИЛИТЫ ---

@dp.message(Command("ping"))
async def cmd_ping(message: types.Message):
    await message.reply("🏓 **Pong!** Бот работает на высоких скоростях 🚀", parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("myid"))
async def cmd_myid(message: types.Message):
    await message.reply(
        f"👤 Твой ID: `{message.from_user.id}`\n"
        f"💬 ID этого чата: `{message.chat.id}`", 
        parse_mode=ParseMode.MARKDOWN
    )

# --- АНИМАЦИЯ И ФОТО (Старые функции) ---

@dp.message(Command("animate_text"))
async def cmd_animate_text(message: types.Message):
    text_to_type = message.text.replace("/animate_text", "").strip()
    if not text_to_type:
        text_to_type = "Вы не ввели текст после команды!"

    current_text = ""
    sent_message = await message.answer("░")
    text_to_type = text_to_type[:50] # Лимит символов от спама
    
    for char in text_to_type:
        current_text += char
        try:
            await sent_message.edit_text(f"{current_text}▋")
            await asyncio.sleep(0.2)
        except Exception:
            pass
    try:
        await sent_message.edit_text(current_text)
    except Exception:
        pass

@dp.message(Command("say"))
async def cmd_say(message: types.Message):
    text_to_say = message.text.replace("/say", "").strip()
    if not text_to_say:
        await message.answer("ℹ️ Использование: `/say Привет чат!`", parse_mode=ParseMode.MARKDOWN)
        return
    await message.answer(text_to_say)

# Агрессивный мемный жмых
def apply_aggressive_jmih(img_stream):
    output_io = io.BytesIO()
    with Image.open(img_stream) as img:
        img = ImageOps.autocontrast(img)
        img = ImageEnhance.Color(img).enhance(1.4)
        orig_width, orig_height = img.size
        distorted = img.resize((int(orig_width * 0.15), orig_height), Image.Resampling.LANCZOS)
        distorted = distorted.resize((int(orig_width * 0.35), int(orig_height * 0.6)), Image.Resampling.LANCZOS)
        distorted = distorted.resize((distorted.width, int(distorted.height * 0.2)), Image.Resampling.LANCZOS)
        distorted = distorted.resize((orig_width, orig_height), Image.Resampling.NEAREST)
        distorted.save(output_io, format="JPEG", quality=20, optimize=True)
        output_io.seek(0)
        return output_io

@dp.message(Command("jmih"))
async def cmd_jmih(message: types.Message):
    photo = None
    if message.photo:
        photo = message.photo[-1]
    elif message.reply_to_message and message.reply_to_message.photo:
        photo = message.reply_to_message.photo[-1]

    if not photo:
        await message.answer("❌ Эта команда работает только как ответ на фото, либо отправляйте фото с подписью `/jmih`!")
        return

    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_PHOTO)
    file_in_io = io.BytesIO()
    await bot.download(photo, destination=file_in_io)
    file_in_io.seek(0)

    try:
        processed_img_io = apply_aggressive_jmih(file_in_io)
        input_file = BufferedInputFile(processed_img_io.read(), filename="jmih_meme.jpg")
        await message.answer_photo(photo=input_file, caption="🥴 **Твоё фото успешно пожмыхано!**", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await message.answer("❌ Ошибка при обработке фото!")
        print(f"DEBUG JMIH ERROR: {e}", file=sys.stderr)

# Запуск
async def main():
    print("Бот с мини-играми успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
