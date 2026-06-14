import os
import asyncio
import sys
import io
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, ChatMemberUpdatedFilter
from aiogram.filters.chat_member_updated import JOIN_TRANSITION
from aiogram.enums import ChatAction
from aiogram.types import BufferedInputFile

# Для работы с фото ("жмыхание")
from PIL import Image

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    print("Ошибка: Переменная окружения BOT_TOKEN не задана!", file=sys.stderr)
    sys.exit(1)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Общий текст справки, чтобы не дублировать код
HELP_TEXT = (
    "🤖 **Я анимированный интерактивный бот Amatka!**\n\n"
    "Вот что я умею делать в чатах:\n"
    "🕵️‍♂️ /mafia_amatka — запустить игру в Мафию\n"
    "✨ `/animate_text <текст>` — сделать красивую анимацию текста\n"
    "🖼 `/jmih` (ответом на фото) — исказить/«жмыхнуть» картинку\n"
    "🗣 `/say <текст>` — сказать заданный текст в чат\n\n"
    "📌 Чтобы вызвать это меню снова, используйте команду /help_amatka"
)

# --- 1. АВТО-ПРИВЕТСТВИЕ ПРИ ДОБАВЛЕНИИ В ЧАТ ---
@dp.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def bot_added_to_chat(event: types.ChatMemberUpdated):
    """Срабатывает, когда бота добавляют в группу или супергруппу"""
    await event.bot.send_message(
        chat_id=event.chat.id,
        text=f"👋 Привет, чат **{event.chat.title}**!\n\n{HELP_TEXT}",
        parse_mode="Markdown"
    )

# --- 2. ПОДСКАЗКИ В ЛИЧНОМ ЧАТЕ (/start) ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Срабатывает при первом запуске бота пользователем в ЛС"""
    if message.chat.type == "private":
        welcome_text = (
            f"👋 Привет, {message.from_user.first_name}!\n\n"
            f"Я отлично работаю как в личных сообщениях, так и в группах.\n\n"
            f"{HELP_TEXT}\n\n"
            f"💡 **Совет:** Добавь меня в свой чат с друзьями, дай права администратора, "
            f"и мы сможем круто проводить время!"
        )
        await message.answer(welcome_text, parse_mode="Markdown")
    else:
        # Если случайно написали /start в группе
        await message.answer(HELP_TEXT, parse_mode="Markdown")

# --- 3. СПРАВКА ПО КОМАНДЕ (/help_amatka) ---
@dp.message(Command("help_amatka"))
async def cmd_help(message: types.Message):
    await message.answer(HELP_TEXT, parse_mode="Markdown")

# --- 4. ИГРА В МАФИЮ ---
@dp.message(Command("mafia_amatka"))
async def cmd_mafia(message: types.Message):
    await message.answer(
        "🕵️‍♂️ *Режим «Мафия» активирован!*\n\n"
        "Город засыпает... Просыпаются мирные жители. Напишите в комментариях, "
        "кто готов играть, а полноценный модуль игры будет доступен в следующем обновлении! 🏙",
        parse_mode="Markdown"
    )

# --- 5. АНИМАЦИЯ ТЕКСТА ---
@dp.message(Command("animate_text"))
async def cmd_animate_text(message: types.Message):
    text_to_type = message.text.replace("/animate_text", "").strip()
    
    if not text_to_type:
        await message.answer("❌ Вы не ввели текст после команды! Попробуйте: `/animate_text Привет всем`", parse_mode="Markdown")
        return

    current_text = ""
    sent_message = await message.answer("░")
    
    # Ограничение длины
    text_to_type = text_to_type[:50]
    
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

# --- 6. ЖМЫХ ФОТО ---
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

    with Image.open(file_in_io) as img:
        original_width, original_height = img.size
        squashed_img = img.resize((int(original_width * 0.3), int(original_height * 0.7)), Image.Resampling.LANCZOS)
        jmih_img = squashed_img.resize((original_width, original_height), Image.Resampling.NEAREST)
        
        output_io = io.BytesIO()
        jmih_img.save(output_io, format="JPEG", quality=40)
        output_io.seek(0)

    input_file = BufferedInputFile(output_io.read(), filename="jmih.jpg")
    await message.answer_photo(photo=input_file, caption="🥴 Твоё фото успешно пожмыхано!")

# --- 7. СКАЗАТЬ ТЕКСТ (/say) ---
@dp.message(Command("say"))
async def cmd_say(message: types.Message):
    text_to_say = message.text.replace("/say", "").strip()
    
    if not text_to_say:
        await message.answer("ℹ️ Использование: `/say Привет чат!` (напишите текст после команды)", parse_mode="Markdown")
        return
        
    await message.answer(text_to_say)

# Запуск
async def main():
    print("Обновленный бот Amatka успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
