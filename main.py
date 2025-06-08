import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# === Конфигурация ===
BOT_TOKEN = "6530969728:AAHU6Rs_HHzCBoWI_xnqAgny2krnE0AaW9Y"  # ← вставь сюда свой токен от @BotFather
ADMIN_ID = 5585811533     # ← вставь сюда свой Telegram ID (узнай в @userinfobot)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# === Хранилище данных ===
products = []
reviews = []

# === Клавиатура ===
def get_main_kb(is_admin=False):
    kb = ReplyKeyboardBuilder()
    kb.button(text="Товары")
    kb.button(text="Отзывы")
    kb.button(text="Инстаграм")
    if is_admin:
        kb.button(text="Добавить товар")
        kb.button(text="Добавить отзыв")
        kb.button(text="Удалить товар")
        kb.button(text="Удалить отзыв")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)

# === FSM ===
class AddProduct(StatesGroup):
    photo = State()
    description = State()
    price = State()

class AddReview(StatesGroup):
    photo = State()

# === Команды ===
@dp.message(Command("start"))
async def start(message: Message):
    is_admin = message.from_user.id == ADMIN_ID
    await message.answer("Привет! Выберите действие:", reply_markup=get_main_kb(is_admin))

@dp.message(F.text == "Инстаграм")
async def instagram(message: Message):
    await message.answer("🌸 Наш Instagram: https://www.instagram.com/florist.giza/")

@dp.message(F.text == "Отзывы")
async def show_reviews(message: Message):
    if not reviews:
        await message.answer("Пока нет отзывов.")
        return
    for photo_id in reviews:
        await message.answer_photo(photo_id)

@dp.message(F.text == "Товары")
async def show_products(message: Message):
    if not products:
        await message.answer("Пока нет товаров.")
        return
    for idx, prod in enumerate(products):
        kb = InlineKeyboardBuilder()
        kb.button(text=f"Купить за {prod['price']:,} сум", callback_data=f"buy:{idx}")
        caption = f"{prod['description']}\nЦена: {prod['price']:,} сум"
        await message.answer_photo(photo=prod["photo_id"], caption=caption, reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("buy:"))
async def handle_buy(callback: CallbackQuery):
    idx = int(callback.data.split(":")[1])
    prod = products[idx]
    user = callback.from_user
    username = user.username or user.full_name or "Без имени"
    await callback.message.answer("✅ Заявка о покупке отправлена!")
    await bot.send_photo(
        ADMIN_ID,
        photo=prod["photo_id"],
        caption=f"🛒 Покупка товара:\n{prod['description']}\nЦена: {prod['price']:,} сум\nПокупатель: @{username}"
    )
    await callback.answer()

# === Добавление товара ===
@dp.message(F.text == "Добавить товар")
async def add_product(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Только для администратора.")
        return
    await message.answer("Отправьте фото товара:")
    await state.set_state(AddProduct.photo)

@dp.message(AddProduct.photo, F.photo)
async def product_photo(message: Message, state: FSMContext):
    await state.update_data(photo_id=message.photo[-1].file_id)
    await message.answer("Теперь отправьте описание товара:")
    await state.set_state(AddProduct.description)

@dp.message(AddProduct.description)
async def product_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("Введите цену в суммах (UZS):")
    await state.set_state(AddProduct.price)

@dp.message(AddProduct.price)
async def product_price(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Цена должна быть числом.")
        return
    data = await state.get_data()
    products.append({
        "photo_id": data["photo_id"],
        "description": data["description"],
        "price": int(message.text)
    })
    await message.answer("✅ Товар добавлен!", reply_markup=get_main_kb(True))
    await state.clear()

# === Добавление отзыва ===
@dp.message(F.text == "Добавить отзыв")
async def add_review(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Только для администратора.")
        return
    await message.answer("Отправьте скриншот отзыва:")
    await state.set_state(AddReview.photo)

@dp.message(AddReview.photo, F.photo)
async def review_photo(message: Message, state: FSMContext):
    reviews.append(message.photo[-1].file_id)
    await message.answer("✅ Отзыв добавлен!", reply_markup=get_main_kb(True))
    await state.clear()

# === Удаление товара ===
@dp.message(F.text == "Удалить товар")
async def delete_product_menu(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Только для администратора.")
        return
    if not products:
        await message.answer("Нет товаров для удаления.")
        return
    for idx, prod in enumerate(products):
        kb = InlineKeyboardBuilder()
        kb.button(text="❌ Удалить", callback_data=f"del_product:{idx}")
        await message.answer_photo(
            photo=prod["photo_id"],
            caption=f"{prod['description']}\nЦена: {prod['price']:,} сум",
            reply_markup=kb.as_markup()
        )

@dp.callback_query(F.data.startswith("del_product:"))
async def delete_product(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Только админ.", show_alert=True)
        return
    idx = int(callback.data.split(":")[1])
    if 0 <= idx < len(products):
        products.pop(idx)
        await callback.message.delete()
        await callback.answer("🗑️ Товар удалён.")

# === Удаление отзыва ===
@dp.message(F.text == "Удалить отзыв")
async def delete_review_menu(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Только для администратора.")
        return
    if not reviews:
        await message.answer("Нет отзывов для удаления.")
        return
    for idx, photo_id in enumerate(reviews):
        kb = InlineKeyboardBuilder()
        kb.button(text="❌ Удалить", callback_data=f"del_review:{idx}")
        await message.answer_photo(photo_id, reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("del_review:"))
async def delete_review(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Только админ.", show_alert=True)
        return
    idx = int(callback.data.split(":")[1])
    if 0 <= idx < len(reviews):
        reviews.pop(idx)
        await callback.message.delete()
        await callback.answer("🗑️ Отзыв удалён.")

# === Запуск ===
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
