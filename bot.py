import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

# =========================
# Переменные окружения
# =========================
TOKEN = os.getenv("TOKEN")
ADMIN_IDS = [
    int(os.getenv("ADMIN_ID1")),
    int(os.getenv("ADMIN_ID2"))
]

if not TOKEN or not all(ADMIN_IDS):
    raise ValueError("Необходимо задать переменные окружения TOKEN, ADMIN_ID1 и ADMIN_ID2")

bot = Bot(token=TOKEN)
dp = Dispatcher()

reply_targets = {}

# =========================
# /start — кнопка Начать
# =========================
@dp.message(F.text == "/start")
async def start(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="▶️ Начать", callback_data="start_chat")]]
    )
    await message.answer("Добро пожаловать! Нажмите кнопку ниже, чтобы продолжить.", reply_markup=keyboard)

# =========================
# Начать → категории
# =========================
@dp.callback_query(F.data == "start_chat")
async def show_categories(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="1", callback_data="cat_1")],
            [InlineKeyboardButton(text="2", callback_data="cat_2")],
            [InlineKeyboardButton(text="3", callback_data="cat_3")],
        ]
    )
    await callback.message.answer("Выберите категорию:", reply_markup=keyboard)
    await callback.answer()

# =========================
# Пользователь выбирает категорию
# =========================
@dp.callback_query(F.data.startswith("cat_"))
async def category_selected(callback: CallbackQuery):
    cat = callback.data.replace("cat_", "")
    user_id = callback.from_user.id
    reply_targets[user_id] = {"category": cat, "awaiting": True}
    await callback.message.answer(f"Категория: *{cat}*\nТеперь напишите ваше сообщение.", parse_mode="Markdown")
    await callback.answer()

# =========================
# Отправка сообщения админам
# =========================
@dp.message()
async def forward_to_admins(message: Message):
    user_id = message.from_user.id
    if user_id not in reply_targets or not reply_targets[user_id]["awaiting"]:
        return

    category = reply_targets[user_id]["category"]
    for admin_id in ADMIN_IDS:
        admin_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="✉️ Ответить", callback_data=f"reply_to_{user_id}")]]
        )
        if message.text:
            await bot.send_message(
                admin_id,
                f"📩 Сообщение от @{message.from_user.username or 'Без имени'} (ID: {user_id})\n"
                f"Категория: *{category}*\n\n"
                f"{message.text}",
                reply_markup=admin_keyboard,
                parse_mode="Markdown"
            )
        else:
            caption = f"📩 Сообщение от @{message.from_user.username or 'Без имени'} (ID: {user_id})\nКатегория: *{category}*"
            await message.send_copy(admin_id, caption=caption, reply_markup=admin_keyboard)

    reply_targets[user_id]["awaiting"] = False
    await message.answer("✅ Ваше сообщение отправлено администраторам!")

# =========================
# Админы отвечают пользователям
# =========================
@dp.callback_query(F.data.startswith("reply_to_"))
async def admin_reply_mode(callback: CallbackQuery):
    user_id = int(callback.data.replace("reply_to_", ""))
    admin_id = callback.from_user.id
    if admin_id not in ADMIN_IDS:
        await callback.answer("❌ Вы не админ!", show_alert=True)
        return

    reply_targets[admin_id] = {"reply_to": user_id, "awaiting": True}
    await callback.message.answer(f"✏️ Напишите ответ для пользователя {user_id}:")
    await callback.answer()

@dp.message(F.chat.id.in_(ADMIN_IDS))
async def send_admin_reply(message: Message):
    admin_id = message.from_user.id
    if not reply_targets.get(admin_id, {}).get("awaiting"):
        return

    target_id = reply_targets[admin_id]["reply_to"]
    try:
        await message.send_copy(target_id)
    except Exception:
        await message.answer("❌ Не удалось отправить сообщение. Пользователь мог заблокировать бота.")
        return

    await message.answer("✅ Ответ отправлен пользователю!")
    reply_targets[admin_id]["awaiting"] = False

# =========================
# Запуск
# =========================
async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
