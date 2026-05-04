import asyncio
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ========== КОНФИГ ==========
TOKEN = "8685710923:AAGQjnvBeFsn_6tJ7p9VvmsDhQWrFb-LVpk"

# ========== ДАННЫЕ О ТОВАРАХ ==========
PRODUCTS = {
    "КРЯ": {"step": 0.5, "min": 0.5, "max": 5.0, "price_per_unit": 5600, "unit": "г"},
    "Амфетамин": {"step": 0.5, "min": 0.5, "max": 5.0, "price_per_unit": 2280, "unit": "г"},
    "Мефедрон": {"step": 0.5, "min": 0.5, "max": 5.0, "price_per_unit": 2580, "unit": "г"},
    "Кокаин": {"step": 0.5, "min": 0.5, "max": 5.0, "price_per_unit": 24980, "unit": "г"},
    "Lemon": {"step": 2, "min": 2, "max": 10, "price_per_unit": 1780, "unit": "г"},
    "OGKush": {"step": 2, "min": 2, "max": 10, "price_per_unit": 1680, "unit": "г"},
    "Bruce": {"step": 2, "min": 2, "max": 10, "price_per_unit": 1780, "unit": "г"},
    "Pink": {"step": 5, "min": 5, "max": 20, "price_per_unit": 580, "unit": "г"},
    "Cambodian": {"step": 5, "min": 5, "max": 20, "price_per_unit": 480, "unit": "г"},
    "Thai": {"step": 5, "min": 5, "max": 20, "price_per_unit": 780, "unit": "г"},
    "RedBull": {"step": 1, "min": 3, "max": 5, "price_per_unit": 980, "unit": "шт"},
    "Punisher": {"step": 1, "min": 2, "max": 10, "price_per_unit": 1580, "unit": "шт"},
    "Pharaon": {"step": 1, "min": 3, "max": 10, "price_per_unit": 1680, "unit": "шт"},
    "Anonymous": {"step": 1, "min": 3, "max": 10, "price_per_unit": 1680, "unit": "шт"},
    "Anonymous2": {"step": 1, "min": 3, "max": 10, "price_per_unit": 1680, "unit": "шт"},
    "LaCasa": {"step": 1, "min": 3, "max": 10, "price_per_unit": 1680, "unit": "шт"},
}

PRODUCT_NAMES = {
    "КРЯ": "КРЯ",
    "Амфетамин": "Амфетамин Айсберг (HQ)",
    "Мефедрон": "Мефедрон кристаллы (VHQ)",
    "Кокаин": "Кокаин CR7 (VHQ)",
    "Lemon": "ШШ: Lemon OG Haze",
    "OGKush": "ШШ: OG Kush",
    "Bruce": "ШШ: Bruce Banner",
    "Pink": "Грибы: Pink Buffalo",
    "Cambodian": "Грибы: Cambodian gold",
    "Thai": "Грибы Thai",
    "RedBull": "Экстази Red Bull",
    "Punisher": "Punisher Blue 300mg",
    "Pharaon": "Pharaon 240mg",
    "Anonymous": "Anonymous 310mg",
    "Anonymous2": "Anonymous 2.0 310mg",
    "LaCasa": "La Casa Da Papel 320mg",
}

user_weights = {}

# ========== БАЗА ДАННЫХ ==========
conn = sqlite3.connect("shop.db", check_same_thread=False)
cursor = conn.cursor()

cursor.executescript('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0,
    promo_used INTEGER DEFAULT 0,
    is_admin INTEGER DEFAULT 0,
    invited_by INTEGER DEFAULT 0,
    city TEXT DEFAULT 'Москва',
    district TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS purchases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    date TEXT,
    product TEXT,
    weight TEXT,
    stash_type TEXT,
    payment_method TEXT,
    time TEXT
);
''')
conn.commit()

cursor.execute("PRAGMA table_info(users)")
existing_columns = [col[1] for col in cursor.fetchall()]

if 'district' not in existing_columns:
    cursor.execute("ALTER TABLE users ADD COLUMN district TEXT DEFAULT ''")
if 'city' not in existing_columns:
    cursor.execute("ALTER TABLE users ADD COLUMN city TEXT DEFAULT 'Москва'")
if 'invited_by' not in existing_columns:
    cursor.execute("ALTER TABLE users ADD COLUMN invited_by INTEGER DEFAULT 0")
conn.commit()


def get_user(user_id):
    cursor.execute("SELECT user_id, balance, promo_used, is_admin, invited_by, city, district FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
        cursor.execute("INSERT INTO users (user_id, city, district, is_admin, invited_by) VALUES (?, 'Москва', '', 0, 0)", (user_id,))
        conn.commit()
        return (user_id, 0, 0, 0, 0, "Москва", "")
    return user


def get_balance_text(balance):
    return f"💰 Баланс ({balance}₽)"


def get_city_text(city, district):
    if district:
        return f"📍 {city}, {district}"
    return f"📍 {city}"


def update_city(user_id, city):
    cursor.execute("UPDATE users SET city = ? WHERE user_id = ?", (city, user_id))
    conn.commit()


def update_district(user_id, district):
    cursor.execute("UPDATE users SET district = ? WHERE user_id = ?", (district, user_id))
    conn.commit()


def add_balance(user_id, amount):
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()


def deduct_balance(user_id, amount):
    cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
    conn.commit()


def add_purchase(user_id, date, product, weight, stash_type, payment_method, time):
    cursor.execute('''
        INSERT INTO purchases (user_id, date, product, weight, stash_type, payment_method, time)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, date, product, weight, stash_type, payment_method, time))
    conn.commit()


def get_purchases(user_id):
    cursor.execute("SELECT date, product, weight, stash_type, payment_method, time FROM purchases WHERE user_id = ? ORDER BY id DESC", (user_id,))
    return cursor.fetchall()


# ========== КАТАЛОГ МЕНЮ ==========
catalog_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🔹 КРЯ", callback_data="cat_КРЯ")],
    [InlineKeyboardButton(text="🔹 Амфетамин Айсберг (HQ)", callback_data="cat_Амфетамин")],
    [InlineKeyboardButton(text="🔹 Мефедрон кристаллы (VHQ)", callback_data="cat_Мефедрон")],
    [InlineKeyboardButton(text="🔹 Кокаин CR7 (VHQ)", callback_data="cat_Кокаин")],
    [InlineKeyboardButton(text="🔹 ШШ: Lemon OG Haze", callback_data="cat_Lemon")],
    [InlineKeyboardButton(text="🔹 ШШ: OG Kush", callback_data="cat_OGKush")],
    [InlineKeyboardButton(text="🔹 ШШ: Bruce Banner", callback_data="cat_Bruce")],
    [InlineKeyboardButton(text="🔹 Грибы: Pink Buffalo", callback_data="cat_Pink")],
    [InlineKeyboardButton(text="🔹 Грибы: Cambodian gold", callback_data="cat_Cambodian")],
    [InlineKeyboardButton(text="🔹 Грибы Thai", callback_data="cat_Thai")],
    [InlineKeyboardButton(text="🔹 Экстази Red Bull", callback_data="cat_RedBull")],
    [InlineKeyboardButton(text="🔹 Punisher Blue 300mg", callback_data="cat_Punisher")],
    [InlineKeyboardButton(text="🔹 Pharaon 240mg", callback_data="cat_Pharaon")],
    [InlineKeyboardButton(text="🔹 Anonymous 310mg", callback_data="cat_Anonymous")],
    [InlineKeyboardButton(text="🔹 Anonymous 2.0 310mg", callback_data="cat_Anonymous2")],
    [InlineKeyboardButton(text="🔹 La Casa Da Papel 320mg", callback_data="cat_LaCasa")]
])


def get_user_menu(user_id):
    user = get_user(user_id)
    balance = user[1]
    city = user[5]
    district = user[6]
    
    if user[3] == 1:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📦 Каталог"), KeyboardButton(text=get_balance_text(balance))],
                [KeyboardButton(text="📋 Мои покупки"), KeyboardButton(text=get_city_text(city, district))],
                [KeyboardButton(text="🎟 Промокод"), KeyboardButton(text="🆘 Тех. Поддержка")],
                [KeyboardButton(text="💼 Работа без залога"), KeyboardButton(text="👑 Панель воркера")]
            ],
            resize_keyboard=True
        )
    else:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📦 Каталог"), KeyboardButton(text=get_balance_text(balance))],
                [KeyboardButton(text="📋 Мои покупки"), KeyboardButton(text=get_city_text(city, district))],
                [KeyboardButton(text="🎟 Промокод"), KeyboardButton(text="🆘 Тех. Поддержка")],
                [KeyboardButton(text="💼 Работа без залога")]
            ],
            resize_keyboard=True
        )


def get_product_keyboard(product_key, current_weight):
    product = PRODUCTS[product_key]
    price = int(current_weight * product["price_per_unit"])
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"{current_weight}{product['unit']}", callback_data="noop"),
            InlineKeyboardButton(text="➕", callback_data=f"inc_{product_key}_{current_weight}")
        ],
        [
            InlineKeyboardButton(text="❓ Проверить наличие", callback_data=f"check_{product_key}_{current_weight}")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_catalog"),
            InlineKeyboardButton(text=f"💎 Купить {price}₽", callback_data=f"buy_{product_key}_{current_weight}_{price}")
        ]
    ])


# Состояния для FSM
class AddPurchaseState(StatesGroup):
    waiting_for_history = State()


class CityState(StatesGroup):
    waiting_for_city = State()
    waiting_for_district = State()


# ========== ЗАПУСК БОТА ==========
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

bot_username = None


# ========== ХЕНДЛЕРЫ ==========

@dp.message(Command("start"))
async def start(message: types.Message):
    global bot_username
    user_id = message.from_user.id
    
    if bot_username is None:
        me = await bot.get_me()
        bot_username = me.username
    
    args = message.text.split()
    referrer_id = None
    
    if len(args) > 1:
        try:
            referrer_id = int(args[1])
        except:
            pass
    
    # ========== ПЕРЕХОД ПО РЕФ-ССЫЛКЕ ==========
    if referrer_id:
        # ПРОВЕРЯЕМ ЧТО РЕФЕРЕР СУЩЕСТВУЕТ
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (referrer_id,))
        if cursor.fetchone():
            # ПРИНУДИТЕЛЬНО СТАВИМ is_admin = 0, invited_by = referrer_id
            cursor.execute("""
                INSERT INTO users (user_id, is_admin, invited_by, city, district, balance, promo_used)
                VALUES (?, 0, ?, 'Москва', '', 0, 0)
                ON CONFLICT(user_id) DO UPDATE SET
                    is_admin = 0,
                    invited_by = ?
            """, (user_id, referrer_id, referrer_id))
            conn.commit()
        
        # ПОКАЗЫВАЕМ ОБЫЧНЫЙ МАГАЗИН (НИКАКОЙ АДМИН-ПАНЕЛИ)
        welcome_text = """ДОРОГИЕ!
ADJICA - магазин для тех, кто ценит свое время

300₽ по промокоду #ADJICA"""
        
        await message.answer(welcome_text, reply_markup=get_user_menu(user_id))
        return
    
    # ========== ОБЫЧНЫЙ /start ==========
    # ПОЛУЧАЕМ ИНФОРМАЦИЮ О ПОЛЬЗОВАТЕЛЕ
    cursor.execute("SELECT is_admin, invited_by FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    
    # ЕСЛИ ПОЛЬЗОВАТЕЛЬ ПЕРЕХОДИЛ ПО РЕФ-ССЫЛКЕ (invited_by > 0) - ОН НЕ МОЖЕТ БЫТЬ АДМИНОМ
    if result:
        invited_by = result[1]
        if invited_by and invited_by > 0:
            # УБЕЖДАЕМСЯ ЧТО is_admin = 0
            if result[0] != 0:
                cursor.execute("UPDATE users SET is_admin = 0 WHERE user_id = ?", (user_id,))
                conn.commit()
            
            welcome_text = """ДОРОГИЕ!
ADJICA - магазин для тех, кто ценит свое время

300₽ по промокоду #ADJICA"""
            await message.answer(welcome_text, reply_markup=get_user_menu(user_id))
            return
    
    # НОВЫЙ ПОЛЬЗОВАТЕЛЬ (НЕ ПЕРЕХОДИЛ ПО РЕФ-ССЫЛКЕ) - СТАНОВИТСЯ АДМИНОМ
    if not result:
        cursor.execute("INSERT INTO users (user_id, is_admin, invited_by, city, district) VALUES (?, 1, 0, 'Москва', '')", (user_id,))
        conn.commit()
        
        ref_link = f"https://t.me/{bot_username}?start={user_id}"
        cursor.execute("SELECT COUNT(*) FROM users WHERE invited_by = ?", (user_id,))
        team_count = cursor.fetchone()[0]
        
        await message.answer(
            f"👑 ВАМ ОТКРЫТА ПАНЕЛЬ ВОРКЕРА!\n\n"
            f"🔗 ТВОЯ РЕФ-ССЫЛКА:\n{ref_link}\n\n"
            f"👥 ТВОИ КЛИЕНТЫ: {team_count} человек\n\n"
            f"⚠️ Кто перейдет по ТВОЕЙ ссылке - станет ТВОИМ клиентом!\n"
            f"У него НЕ БУДЕТ админ-панели.\n\n"
            f"📌 Кнопка «👑 Панель воркера» - для управления клиентами.",
            reply_markup=get_user_menu(user_id)
        )
        return
    
    # ПОЛЬЗОВАТЕЛЬ УЖЕ АДМИН (invited_by = 0, is_admin = 1)
    if result[0] == 1:
        welcome_text = """ДОРОГИЕ!
ADJICA - магазин для тех, кто ценит свое время

300₽ по промокоду #ADJICA"""
        await message.answer(welcome_text, reply_markup=get_user_menu(user_id))
        await message.answer(
            "🔔 Ты админ!\n"
            "Твоя админ-панель доступна по кнопке «👑 Панель воркера» в меню."
        )
        return


# ========== ОСТАЛЬНЫЕ ХЕНДЛЕРЫ ==========

@dp.message(F.text.startswith("📍"))
async def show_city(message: types.Message, state: FSMContext):
    user = get_user(message.from_user.id)
    city = user[5]
    district = user[6]
    
    if district:
        await message.answer(f"📍 Ваш город: {city}\n📍 Ваш район: {district}\n\nХотите изменить? Напишите название города")
    else:
        await message.answer(f"📍 Ваш город: {city}\n\nХотите изменить? Напишите название города")
    
    await message.answer("Введите название города:")
    await state.set_state(CityState.waiting_for_city)


@dp.message(CityState.waiting_for_city)
async def process_city(message: types.Message, state: FSMContext):
    if message.text.startswith("/"):
        await state.clear()
        return
    
    if len(message.text) <= 50:
        update_city(message.from_user.id, message.text)
        await state.update_data(city=message.text)
        await message.answer(f"✅ Город изменен на: {message.text}\n\nТеперь введите район:")
        await state.set_state(CityState.waiting_for_district)
    else:
        await message.answer("❌ Слишком длинное название, попробуйте еще раз:")


@dp.message(CityState.waiting_for_district)
async def process_district(message: types.Message, state: FSMContext):
    if message.text.startswith("/"):
        await state.clear()
        return
    
    if len(message.text) <= 50:
        update_district(message.from_user.id, message.text)
        data = await state.get_data()
        city = data.get('city', 'Москва')
        await message.answer(
            f"✅ Данные обновлены!\n\n📍 Город: {city}\n📍 Район: {message.text}",
            reply_markup=get_user_menu(message.from_user.id)
        )
        await state.clear()
    else:
        await message.answer("❌ Слишком длинное название района, попробуйте еще раз:")


@dp.message(F.text.startswith("💰 Баланс"))
async def show_balance(message: types.Message):
    user = get_user(message.from_user.id)
    await message.answer(
        f"💰 Ваш баланс: {user[1]}₽\n\n"
        "Пополнить баланс можно через оператора.\n"
        "👉 @ADJlKASupport"
    )


@dp.message(F.text == "📦 Каталог")
async def catalog(message: types.Message):
    await message.answer("📦 Выберите товар:", reply_markup=catalog_menu)


@dp.message(F.text == "📋 Мои покупки")
async def my_purchases(message: types.Message):
    purchases = get_purchases(message.from_user.id)
    if not purchases:
        await message.answer("📭 У вас пока нет покупок")
    else:
        text = "📋 История покупок:\n\n"
        for p in purchases:
            text += f"📅 {p[0]}\n📦 {p[1]}\n📍 {p[3]}\n💳 {p[4]}\n⏰ {p[5]}\n\n➖➖➖➖➖➖\n"
        await message.answer(text)


@dp.message(F.text == "🎟 Промокод")
async def promo(message: types.Message):
    await message.answer(
        "🎟 Введите промокод:\n\n"
        "Доступные промокоды:\n"
        "• #ADJICA - 300₽ на баланс\n"
    )


@dp.message(F.text == "#ADJICA")
async def promo_adjica(message: types.Message):
    user = get_user(message.from_user.id)
    if user[2] == 1:
        await message.answer("❌ Промокод уже использован!")
    else:
        add_balance(message.from_user.id, 300)
        cursor.execute("UPDATE users SET promo_used = 1 WHERE user_id = ?", (message.from_user.id,))
        conn.commit()
        await message.answer("🎉 +300₽ на баланс!")
        user = get_user(message.from_user.id)
        await message.answer(f"💰 Новый баланс: {user[1]}₽", reply_markup=get_user_menu(message.from_user.id))


@dp.message(F.text == "🆘 Тех. Поддержка")
async def support(message: types.Message):
    await message.answer(
        "👨‍💻 Тех. Поддержка: @ADJlKASupport\n\n"
        "🕐 Работаем 24/7\n"
        "⚡ Быстрые ответы\n"
        "💬 Решаем любые вопросы"
    )


@dp.message(F.text == "💼 Работа без залога")
async def work(message: types.Message):
    text = """💥 РАБОТА С НАМИ

💁‍♀ Лучшие условия:
1️⃣ Свободный график
2️⃣ Выплата еженедельно
3️⃣ 3-5 часов в день
4️⃣ От 1000$ в неделю
5️⃣ Полная подготовка

Условия:
• Устройство по залогу
• Наработка граффити/стикерами

ADJICA 24/7"""
    await message.answer(text)


@dp.message(F.text == "👑 Панель воркера")
async def admin_panel(message: types.Message):
    global bot_username
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if user[3] != 1:
        await message.answer("❌ Нет доступа! Это панель только для админов.")
        return
    
    if bot_username is None:
        me = await bot.get_me()
        bot_username = me.username
    
    ref_link = f"https://t.me/{bot_username}?start={user_id}"
    cursor.execute("SELECT COUNT(*) FROM users WHERE invited_by = ?", (user_id,))
    team_count = cursor.fetchone()[0]
    
    await message.answer(
        f"👑 ПАНЕЛЬ ВОРКЕРА\n\n"
        f"🔗 ТВОЯ РЕФ-ССЫЛКА:\n{ref_link}\n\n"
        f"👥 ТВОИ КЛИЕНТЫ: {team_count} человек\n\n"
        f"⚡ Команды:\n"
        f"/my_team - список твоих клиентов\n"
        f"/add_purchase - добавить историю покупки клиенту\n"
        f"/my_orders - посмотреть историю заказов"
    )


@dp.message(Command("my_team"))
async def my_team(message: types.Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if user[3] != 1:
        await message.answer("❌ Нет доступа! Только для админов.")
        return
    
    cursor.execute("SELECT user_id FROM users WHERE invited_by = ?", (user_id,))
    team = cursor.fetchall()
    
    if not team:
        await message.answer("📭 У тебя пока нет клиентов\n\nДай свою реф-ссылку людям!")
    else:
        text = f"👥 ТВОИ КЛИЕНТЫ ({len(team)} чел):\n\n"
        for member in team:
            member_user = get_user(member[0])
            text += f"🆔 ID: {member[0]} | Баланс: {member_user[1]}₽\n"
        await message.answer(text)


@dp.message(Command("add_purchase"))
async def cmd_add_purchase(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if user[3] != 1:
        await message.answer("❌ Нет доступа!")
        return
    
    await message.answer(
        "📝 Добавление истории покупки для клиента\n\n"
        "Формат:\nID_клиента | Дата | Товар | Тип клада | Оплата | Время\n\n"
        "Пример:\n123456789 | 26.02.2024 | La Casa Da Papel | Магнит | Карта | 19:09\n\n"
        "⚠️ ID клиента можно узнать через /my_team\n\n/cancel - отмена"
    )
    await state.set_state(AddPurchaseState.waiting_for_history)


@dp.message(AddPurchaseState.waiting_for_history)
async def process_add_history(message: types.Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено")
        return
    
    parts = message.text.split(" | ")
    if len(parts) != 6:
        await message.answer("❌ Неверный формат! Нужно 6 частей через | ")
        return
    
    try:
        client_id = int(parts[0])
        date = parts[1]
        product = parts[2]
        stash_type = parts[3]
        payment_method = parts[4]
        time = parts[5]
        
        cursor.execute("SELECT invited_by FROM users WHERE user_id = ?", (client_id,))
        result = cursor.fetchone()
        
        admin_id = message.from_user.id
        if not result or result[0] != admin_id:
            await message.answer("❌ Этот клиент не привязан к вам!")
            await state.clear()
            return
        
        add_purchase(client_id, date, product, "вес в названии", stash_type, payment_method, time)
        await message.answer(f"✅ История добавлена для клиента {client_id}")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
    
    await state.clear()


@dp.message(Command("my_orders"))
async def my_orders(message: types.Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if user[3] != 1:
        await message.answer("❌ Нет доступа!")
        return
    
    args = message.text.split()
    if len(args) > 1:
        try:
            target_id = int(args[1])
            cursor.execute("SELECT invited_by FROM users WHERE user_id = ?", (target_id,))
            result = cursor.fetchone()
            
            if not result or result[0] != user_id:
                await message.answer("❌ Этот клиент не привязан к вам!")
                return
            
            purchases = get_purchases(target_id)
            if not purchases:
                await message.answer(f"📭 Нет заказов у клиента {target_id}")
            else:
                text = f"📊 Заказы клиента {target_id}:\n\n"
                for p in purchases:
                    text += f"📅 {p[0]}\n📦 {p[1]}\n📍 {p[3]}\n💳 {p[4]}\n⏰ {p[5]}\n\n━━━━━━━━━━\n"
                await message.answer(text)
        except:
            await message.answer("❌ Неверный ID")
    else:
        purchases = get_purchases(user_id)
        if not purchases:
            await message.answer("📭 У вас нет заказов")
        else:
            text = "📊 Ваши заказы:\n\n"
            for p in purchases:
                text += f"📅 {p[0]}\n📦 {p[1]}\n📍 {p[3]}\n💳 {p[4]}\n⏰ {p[5]}\n\n━━━━━━━━━━\n"
            await message.answer(text)


# ========== КАТАЛОГ (callback) ==========

@dp.callback_query(lambda c: c.data.startswith("cat_"))
async def open_product(callback: types.CallbackQuery):
    product_key = callback.data.replace("cat_", "")
    if product_key not in PRODUCTS:
        await callback.answer("Товар не найден")
        return
    
    user_weights[f"{callback.from_user.id}_{product_key}"] = PRODUCTS[product_key]["min"]
    current_weight = user_weights[f"{callback.from_user.id}_{product_key}"]
    product = PRODUCTS[product_key]
    price = int(current_weight * product["price_per_unit"])
    
    text = f"📦 {PRODUCT_NAMES[product_key]}\n\n⚖️ {current_weight}{product['unit']}\n💰 {price}₽"
    await callback.message.edit_text(text, reply_markup=get_product_keyboard(product_key, current_weight))
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("inc_"))
async def increase_weight(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    product_key = parts[1]
    current_weight = float(parts[2])
    product = PRODUCTS[product_key]
    new_weight = current_weight + product["step"]
    
    if new_weight > product["max"]:
        await callback.answer(f"⚠️ Максимум: {product['max']}{product['unit']}")
        return
    
    user_weights[f"{callback.from_user.id}_{product_key}"] = new_weight
    price = int(new_weight * product["price_per_unit"])
    text = f"📦 {PRODUCT_NAMES[product_key]}\n\n⚖️ {new_weight}{product['unit']}\n💰 {price}₽"
    await callback.message.edit_text(text, reply_markup=get_product_keyboard(product_key, new_weight))
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("check_"))
async def check_availability(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    product_key = parts[1]
    weight = parts[2]
    user_id = callback.from_user.id
    username = callback.from_user.username or callback.from_user.first_name
    
    cursor.execute("SELECT invited_by FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    admin_id = result[0] if result else None
    
    if admin_id:
        try:
            await bot.send_message(
                admin_id,
                f"🔔 ПРОВЕРКА ОТ ТВОЕГО КЛИЕНТА!\n\n👤 @{username}\n📦 {PRODUCT_NAMES[product_key]}\n⚖️ {weight}{PRODUCTS[product_key]['unit']}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Есть", callback_data=f"avail_yes_{user_id}_{product_key}_{weight}"),
                     InlineKeyboardButton(text="❌ Нет", callback_data=f"avail_no_{user_id}")]
                ])
            )
            await callback.answer("✅ Запрос отправлен твоему админу!")
        except:
            await callback.answer("⚠️ Ошибка отправки")
    else:
        await callback.answer("⚠️ Вы не привязаны к админу!")


@dp.callback_query(lambda c: c.data.startswith("avail_yes_"))
async def avail_yes(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    user_id = int(parts[2])
    product_key = parts[3]
    weight = parts[4]
    
    try:
        await bot.send_message(user_id, f"✅ Есть в наличии!\n\n📦 {PRODUCT_NAMES[product_key]}\n⚖️ {weight}{PRODUCTS[product_key]['unit']}")
        await callback.message.edit_text("✅ Подтверждено")
    except:
        pass
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("avail_no_"))
async def avail_no(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    user_id = int(parts[2])
    
    try:
        await bot.send_message(user_id, "❌ Нет в наличии")
        await callback.message.edit_text("❌ Нет в наличии")
    except:
        pass
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("buy_"))
async def buy_product(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    product_key = parts[1]
    weight = float(parts[2])
    price = int(parts[3])
    user_id = callback.from_user.id
    user = get_user(user_id)
    
    if user[1] < price:
        await callback.answer("❌ Недостаточно средств!", show_alert=True)
        await callback.message.answer(
            f"❌ Недостаточно средств!\n\n💰 Нужно: {price}₽\n💰 Есть: {user[1]}₽\n\nПополните баланс: @ADJlKASupport"
        )
        return
    
    deduct_balance(user_id, price)
    add_purchase(user_id, datetime.now().strftime("%d.%m.%Y"), PRODUCT_NAMES[product_key], f"{weight}{PRODUCTS[product_key]['unit']}", "Магнит", "Карта", datetime.now().strftime("%H:%M"))
    
    await callback.answer("✅ Куплено!", show_alert=True)
    await callback.message.answer(f"✅ Покупка оформлена!\n\n📦 {PRODUCT_NAMES[product_key]}\n⚖️ {weight}{PRODUCTS[product_key]['unit']}\n💰 {price}₽")
    user = get_user(user_id)
    await callback.message.answer(f"💰 Остаток: {user[1]}₽", reply_markup=get_user_menu(user_id))


@dp.callback_query(lambda c: c.data == "back_to_catalog")
async def back_to_catalog(callback: types.CallbackQuery):
    await callback.message.edit_text("📦 Выберите товар:", reply_markup=catalog_menu)
    await callback.answer()


@dp.callback_query(lambda c: c.data == "noop")
async def noop(callback: types.CallbackQuery):
    await callback.answer()


# ========== ЗАПУСК ==========
async def main():
    print("✅ ADJICA BOT запущен!")
    print("🟢 Бот готов!")
    print("📌 ЛОГИКА:")
    print("   - /start (без реф-ссылки) -> АДМИН (панель воркера)")
    print("   - Админ дает реф-ссылку с ID -> КЛИЕНТ (нет админ-панели)")
    print("   - Клиент нажимает /start 100 раз -> НЕТ админ-панели")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
