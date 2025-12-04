"""
🏆 Warzone Bot - نسخه کامل و اصلاح شده
"""

import asyncio
import logging
import sqlite3
import random
import time
import os
import sys
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

# ==================== CONFIG ====================
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
DEVELOPER_ID = os.getenv("DEVELOPER_ID", "")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== DATABASE ====================
class Database:
    def __init__(self):
        self.db_path = "warzone.db"
        self.setup_database()
    
    def setup_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # جدول کاربران
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                coins INTEGER DEFAULT 1000,
                gems INTEGER DEFAULT 0,
                zp INTEGER DEFAULT 500,
                level INTEGER DEFAULT 1,
                xp INTEGER DEFAULT 0,
                defense_level INTEGER DEFAULT 1,
                miner_level INTEGER DEFAULT 1,
                last_miner_time INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول موشک‌ها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS missiles (
                user_id INTEGER,
                missile_type TEXT,
                quantity INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, missile_type)
            )
        ''')
        
        # جدول جنگنده‌ها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fighters (
                user_id INTEGER,
                fighter_type TEXT,
                quantity INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, fighter_type)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ دیتابیس راه‌اندازی شد")
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def get_user(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
        return user
    
    def create_user(self, user_id, username, full_name):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)', 
                      (user_id, username, full_name))
        conn.commit()
        conn.close()
    
    def update_resource(self, user_id, resource, amount):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if resource == "coins":
            cursor.execute('UPDATE users SET coins = coins + ? WHERE user_id = ?', (amount, user_id))
        elif resource == "gems":
            cursor.execute('UPDATE users SET gems = gems + ? WHERE user_id = ?', (amount, user_id))
        elif resource == "zp":
            cursor.execute('UPDATE users SET zp = zp + ? WHERE user_id = ?', (amount, user_id))
        elif resource == "xp":
            cursor.execute('UPDATE users SET xp = xp + ? WHERE user_id = ?', (amount, user_id))
        
        conn.commit()
        conn.close()
    
    def add_missile(self, user_id, missile_type, quantity=1):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO missiles (user_id, missile_type, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, missile_type) 
            DO UPDATE SET quantity = quantity + ?
        ''', (user_id, missile_type, quantity, quantity))
        conn.commit()
        conn.close()
    
    def add_fighter(self, user_id, fighter_type, quantity=1):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO fighters (user_id, fighter_type, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, fighter_type) 
            DO UPDATE SET quantity = quantity + ?
        ''', (user_id, fighter_type, quantity, quantity))
        conn.commit()
        conn.close()

# ==================== KEYBOARDS ====================
def get_main_keyboard():
    """کیبورد اصلی کامل"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎮 پنل جنگجو"), KeyboardButton(text="⚔️ حمله")],
            [KeyboardButton(text="🏪 بازار جنگ"), KeyboardButton(text="⛏️ ماینر")],
            [KeyboardButton(text="🛡️ پدافند"), KeyboardButton(text="🛩️ جنگنده‌ها")],
            [KeyboardButton(text="🎁 باکس‌ها"), KeyboardButton(text="📞 پشتیبانی")],
            [KeyboardButton(text="🏆 رده‌بندی"), KeyboardButton(text="ℹ️ راهنما")]
        ],
        resize_keyboard=True
    )

def get_warrior_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💰 کیف پول", callback_data="wallet")],
            [InlineKeyboardButton(text="🚀 زرادخانه", callback_data="arsenal")],
            [InlineKeyboardButton(text="📊 آمار من", callback_data="stats")],
            [InlineKeyboardButton(text="⬅️ بازگشت", callback_data="main_menu")]
        ]
    )

def get_market_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💣 موشک‌ها", callback_data="market_missiles")],
            [InlineKeyboardButton(text="🛩️ جنگنده‌ها", callback_data="market_fighters")],
            [InlineKeyboardButton(text="🏰 ارتقای پایگاه", callback_data="market_base")],
            [InlineKeyboardButton(text="⬅️ بازگشت", callback_data="main_menu")]
        ]
    )

def get_miner_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⛏️ برداشت ZP", callback_data="miner_claim")],
            [InlineKeyboardButton(text="⬆️ ارتقای ماینر", callback_data="miner_upgrade")],
            [InlineKeyboardButton(text="📊 اطلاعات ماینر", callback_data="miner_info")],
            [InlineKeyboardButton(text="⬅️ بازگشت", callback_data="main_menu")]
        ]
    )

def get_defense_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛡️ برج سایبری", callback_data="defense_cyber")],
            [InlineKeyboardButton(text="🚀 موشک دفاعی", callback_data="defense_missile")],
            [InlineKeyboardButton(text="🛡️ ضد جنگنده", callback_data="defense_anti")],
            [InlineKeyboardButton(text="📊 وضعیت دفاع", callback_data="defense_status")],
            [InlineKeyboardButton(text="⬅️ بازگشت", callback_data="main_menu")]
        ]
    )

def get_attack_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚡ حمله سریع", callback_data="attack_fast")],
            [InlineKeyboardButton(text="💥 حمله ترکیبی", callback_data="attack_combo")],
            [InlineKeyboardButton(text="☢️ حمله هسته‌ای", callback_data="attack_nuke")],
            [InlineKeyboardButton(text="⬅️ بازگشت", callback_data="main_menu")]
        ]
    )

def get_box_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📦 باکس سکه (1000)", callback_data="box_coin")],
            [InlineKeyboardButton(text="💎 باکس جم (1500)", callback_data="box_gem")],
            [InlineKeyboardButton(text="🎯 باکس ZP (2000)", callback_data="box_zp")],
            [InlineKeyboardButton(text="🏆 باکس افسانه‌ای (5 جم)", callback_data="box_legend")],
            [InlineKeyboardButton(text="⬅️ بازگشت", callback_data="main_menu")]
        ]
    )

def get_support_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📩 تماس با ادمین", callback_data="contact_admin")],
            [InlineKeyboardButton(text="📋 قوانین", callback_data="support_rules")],
            [InlineKeyboardButton(text="🆘 گزارش باگ", callback_data="report_bug")],
            [InlineKeyboardButton(text="⬅️ بازگشت", callback_data="main_menu")]
        ]
    )

def get_back_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ بازگشت", callback_data="main_menu")]
        ]
    )

# ==================== GAME DATA ====================
MISSILES = [
    {"name": "موشک کوتاه‌برد", "price": 100, "damage": 30, "level": 1},
    {"name": "موشک میان‌برد", "price": 250, "damage": 50, "level": 2},
    {"name": "موشک بالستیک", "price": 500, "damage": 80, "level": 3},
    {"name": "موشک هدایت‌شونده", "price": 1000, "damage": 120, "level": 4},
    {"name": "موشک زمین به هوا", "price": 2000, "damage": 180, "level": 5},
    {"name": "موشک هسته‌ای", "price": 5000, "damage": 300, "level": 10, "gems": 3}
]

FIGHTERS = [
    {"name": "فانتوم F-4", "price": 500, "bonus": 10, "level": 1},
    {"name": "میگ-۲۹", "price": 1000, "bonus": 20, "level": 2},
    {"name": "سوخو-۳۵", "price": 2000, "bonus": 35, "level": 3},
    {"name": "F-22 رپتور", "price": 4000, "bonus": 50, "level": 4},
    {"name": "F-35 لایتنینگ", "price": 8000, "bonus": 70, "level": 5}
]

# ==================== BOT INIT ====================
bot = Bot(token=TOKEN)
dp = Dispatcher()
db = Database()

# ==================== START HANDLER ====================
@dp.message(CommandStart())
async def start_command(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "ندارد"
    full_name = message.from_user.full_name
    
    db.create_user(user_id, username, full_name)
    
    text = f"""
🚀 **به Warzone خوش آمدی، {full_name}!**

⚔️ **تو فرمانده یک پایگاه نظامی هستی!**

💰 **منابع اولیه:**
• سکه: 1,000
• جم: 0 (فقط از ادمین یا باکس)
• ZP: 500

⛏️ **ماینر:** سطح 1 - 100 ZP/ساعت
🛡️ **پدافند:** سطح 1

🎯 **ماموریت:** رهبری پایگاه، حمله به دشمنان، صعود در رده‌بندی!
"""
    await message.answer(text, reply_markup=get_main_keyboard())

# ==================== MAIN MENU HANDLERS ====================
@dp.message(F.text == "🎮 پنل جنگجو")
async def warrior_panel(message: Message):
    text = """
🎮 **پنل جنگجو**

در این بخش می‌توانی:
• موجودی منابع را ببینی
• زرادخانه موشک‌ها را مدیریت کنی
• آمار کامل خود را مشاهده کنی
"""
    await message.answer(text, reply_markup=get_warrior_keyboard())

@dp.message(F.text == "🏪 بازار جنگ")
async def market_panel(message: Message):
    text = """
🏪 **بازار جنگ**

اینجا می‌توانی تجهیزات نظامی بخری:

💣 **موشک‌ها:** برای حمله
🛩️ **جنگنده‌ها:** افزایش قدرت حمله
🏰 **ارتقای پایگاه:** تقویت پدافند

💰 **قیمت‌ها مناسب و متعادل!**
"""
    await message.answer(text, reply_markup=get_market_keyboard())

@dp.message(F.text == "⛏️ ماینر")
async def miner_panel(message: Message):
    user = db.get_user(message.from_user.id)
    if user:
        miner_level = user[9]
        income = miner_level * 100
        
        text = f"""
⛏️ **سیستم ماینر**

💰 **درآمد:** {income} ZP در ساعت
📊 **سطح:** {miner_level}
⏰ **برداشت:** هر 1 ساعت

⬆️ **ارتقا:** {miner_level * 150} سکه
"""
    else:
        text = "⚠️ اول /start رو بزن!"
    
    await message.answer(text, reply_markup=get_miner_keyboard())

@dp.message(F.text == "🛡️ پدافند")
async def defense_panel(message: Message):
    text = """
🛡️ **سیستم پدافند**

دفاع پایگاه خود را تقویت کن:

• 🛡️ **برج سایبری:** کاهش damage دشمن
• 🚀 **موشک دفاعی:** انهدام موشک‌های مهاجم  
• 🛡️ **ضد جنگنده:** مقابله با جنگنده‌ها

💪 هرچه دفاع قوی‌تر، آسیب کمتر!
"""
    await message.answer(text, reply_markup=get_defense_keyboard())

@dp.message(F.text == "🛩️ جنگنده‌ها")
async def fighters_panel(message: Message):
    user_id = message.from_user.id
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT fighter_type, quantity FROM fighters WHERE user_id = ?', (user_id,))
    user_fighters = cursor.fetchall()
    conn.close()
    
    text = "🛩️ **ناوگان جنگنده‌های شما**\n\n"
    
    if user_fighters:
        for fighter in user_fighters:
            f_type, quantity = fighter
            text += f"• {f_type}: {quantity} عدد\n"
    else:
        text += "📭 **هنوز جنگنده ندارید!**\n\n"
    
    text += "\n🏪 به بازار جنگ بروید و جنگنده بخرید!"
    
    await message.answer(text, reply_markup=get_back_keyboard())

@dp.message(F.text == "🎁 باکس‌ها")
async def boxes_panel(message: Message):
    text = """
🎁 **باکس‌های شگفت‌انگیز**

شانس خود را برای بردن جوایز عالی امتحان کن:

📦 **باکس سکه:** 1000 سکه - جایزه: 200-2000 سکه
💎 **باکس جم:** 1500 سکه - جایزه: 1-5 جم  
🎯 **باکس ZP:** 2000 سکه - جایزه: 100-500 ZP
🏆 **باکس افسانه‌ای:** 5 جم - جایزه: ترکیبی ویژه

🎰 **شانس برنده شدن بالا!**
"""
    await message.answer(text, reply_markup=get_box_keyboard())

@dp.message(F.text == "⚔️ حمله")
async def attack_panel(message: Message):
    text = """
⚔️ **سیستم حمله**

🎯 **انواع حمله:**

⚡ **حمله سریع:** با یک موشک - 1x damage
💥 **حمله ترکیبی:** موشک + جنگنده - 1.5x damage
☢️ **حمله هسته‌ای:** موشک هسته‌ای - 3x damage

📝 **نحوه حمله:** روی پیام کاربر ریپلای کن و حمله رو انتخاب کن!
"""
    await message.answer(text, reply_markup=get_attack_keyboard())

@dp.message(F.text == "📞 پشتیبانی")
async def support_panel(message: Message):
    text = f"""
📞 **سیستم پشتیبانی**

🤝 **برای ارتباط با ادمین:**

• گزارش باگ و مشکل
• سوال درباره بازی
• پیشنهاد و انتقاد

👨‍💻 **توسعه‌دهنده:** @{DEVELOPER_ID}
⏰ **پاسخگویی:** 24 ساعته

⚠️ **قوانین:** احترام متقابل، عدم اسپم
"""
    await message.answer(text, reply_markup=get_support_keyboard())

@dp.message(F.text == "🏆 رده‌بندی")
async def rankings_panel(message: Message):
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT username, zp, level FROM users ORDER BY zp DESC LIMIT 10')
    top_users = cursor.fetchall()
    conn.close()
    
    text = "🏆 **رده‌بندی برترین فرماندهان**\n\n"
    
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    
    for i, user in enumerate(top_users):
        username = user[0] or "ناشناس"
        zp = user[1]
        level = user[2]
        
        if i < 3:
            text += f"{medals[i]} **{username}**\n"
        else:
            text += f"{i+1}. **{username}**\n"
        
        text += f"   🎯 ZP: {zp:,} | 📊 سطح: {level}\n\n"
    
    if not top_users:
        text += "هنوز کاربری وجود ندارد!\n\n"
    
    text += "💪 برای صعود بیشتر ZP کسب کن!"
    
    await message.answer(text, reply_markup=get_back_keyboard())

@dp.message(F.text == "ℹ️ راهنما")
async def help_panel(message: Message):
    text = """
ℹ️ **راهنمای کامل Warzone**

🎮 **اهداف بازی:**
1. جمع‌آوری منابع (سکه، جم، ZP)
2. تقویت پایگاه و نیروها
3. حمله به کاربران دیگر
4. صعود در رده‌بندی

💰 **اقتصاد:**
• هر ساعت از ماینر برداشت کن
• با ZP در رده‌بندی صعود کن
• از باکس‌ها جایزه بگیر

⚔️ **حمله:**
• روی پیام کاربر ریپلای کن
• از جنگنده‌ها برای damage بیشتر استفاده کن
• پدافند دشمن را در نظر بگیر

🛡️ **دفاع:**
• پدافند خود را ارتقا بده
• از حملات در امان بمان
• منابع خود را حفظ کن

📞 **پشتیبانی:** همیشه در دسترس!
"""
    await message.answer(text, reply_markup=get_back_keyboard())

# ==================== CALLBACK HANDLERS ====================
@dp.callback_query(F.data == "main_menu")
async def back_to_main(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("🏠 منوی اصلی:", reply_markup=get_main_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "wallet")
async def show_wallet(callback: CallbackQuery):
    user = db.get_user(callback.from_user.id)
    
    if user:
        text = f"""
💰 **کیف پول شما**

🪙 **سکه:** {user[3]:,}
💎 **جم:** {user[4]:,}
🎯 **ZP:** {user[5]:,}

📊 **وضعیت:**
• سطح: {user[6]}
• XP: {user[7]}/1000
• پدافند: سطح {user[8]}
• ماینر: سطح {user[9]}
"""
    else:
        text = "⚠️ ابتدا ثبت‌نام کن!"
    
    await callback.message.edit_text(text, reply_markup=get_back_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "arsenal")
async def show_arsenal(callback: CallbackQuery):
    user_id = callback.from_user.id
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT missile_type, quantity FROM missiles WHERE user_id = ?', (user_id,))
    user_missiles = cursor.fetchall()
    conn.close()
    
    text = "🚀 **زرادخانه موشک‌های شما**\n\n"
    
    if user_missiles:
        total = 0
        for missile in user_missiles:
            m_type, quantity = missile
            text += f"• {m_type}: {quantity} عدد\n"
            total += quantity
        text += f"\n📊 **مجموع:** {total} موشک"
    else:
        text += "📭 **هنوز موشک ندارید!**\n\n🏪 به بازار جنگ بروید و موشک بخرید!"
    
    await callback.message.edit_text(text, reply_markup=get_back_keyboard())
    await callback.answer()

# ==================== MARKET HANDLERS ====================
@dp.callback_query(F.data == "market_missiles")
async def market_missiles(callback: CallbackQuery):
    text = "💣 **موشک‌های قابل خرید:**\n\n"
    
    buttons = []
    for missile in MISSILES:
        if "gems" in missile:
            price_text = f"{missile['price']} سکه + {missile['gems']} جم"
            btn_text = f"{missile['name']} - {price_text}"
        else:
            btn_text = f"{missile['name']} - {missile['price']} سکه"
        
        btn_data = f"buy_missile_{missile['name']}"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=btn_data)])
    
    buttons.append([InlineKeyboardButton(text="⬅️ بازگشت", callback_data="main_menu")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    for missile in MISSILES:
        text += f"• **{missile['name']}**\n"
        text += f"  ⚡ Damage: {missile['damage']}\n"
        if "gems" in missile:
            text += f"  💰 قیمت: {missile['price']} سکه + {missile['gems']} جم\n"
        else:
            text += f"  💰 قیمت: {missile['price']} سکه\n"
        text += f"  📊 سطح: {missile['level']}\n\n"
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

# از خط 600 به بعد:

@dp.callback_query(F.data.startswith("buy_missile_"))
async def buy_missile(callback: CallbackQuery):
    missile_name = callback.data.replace("buy_missile_", "")
    
    # پیدا کردن موشک
    missile_data = None
    for missile in MISSILES:
        if missile["name"] == missile_name:
            missile_data = missile
            break
    
    if not missile_data:
        await callback.answer("❌ موشک یافت نشد!", show_alert=True)
        return
    
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await callback.answer("⚠️ ابتدا ثبت‌نام کن!", show_alert=True)
        return
    
    # چک کردن سطح
    if user[6] < missile_data["level"]:
        await callback.answer(f"❌ سطح کافی نیست! نیاز: سطح {missile_data['level']}", show_alert=True)
        return
    
    # چک کردن منابع
    if user[3] < missile_data["price"]:
        await callback.answer(f"❌ سکه کافی نیست! نیاز: {missile_data['price']} سکه", show_alert=True)
        return
    
    # چک کردن جم اگر موشک نیاز دارد
    if "gems" in missile_data and missile_data["gems"] > 0 and user[4] < missile_data["gems"]:
        await callback.answer(f"❌ جم کافی نیست! نیاز: {missile_data['gems']} جم", show_alert=True)
        return
    
    # خرید موشک
    db.update_resource(user_id, "coins", -missile_data["price"])
    
    # کم کردن جم اگر نیاز دارد
    if "gems" in missile_data and missile_data["gems"] > 0:
        db.update_resource(user_id, "gems", -missile_data["gems"])
        cost_text = f"{missile_data['price']} سکه + {missile_data['gems']} جم"
    else:
        cost_text = f"{missile_data['price']} سکه"
    
    db.add_missile(user_id, missile_name)
    
    # دریافت اطلاعات جدید
    user = db.get_user(user_id)
    
    text = f"""
✅ **خرید موفق!**

💣 **{missile_name}** خریداری شد!
⚡ Damage: {missile_data['damage']}
💰 هزینه: {cost_text}
📦 تعداد: 1 عدد

💎 **باقی‌مانده:**
• سکه: {user[3]:,}
• جم: {user[4]:,}
"""
    
    await callback.message.edit_text(text, reply_markup=get_back_keyboard())
    await callback.answer("✅ خرید شد!")
# ==================== MINER HANDLERS ====================
@dp.callback_query(F.data == "miner_claim")
async def claim_miner(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await callback.answer("⚠️ ابتدا ثبت‌نام کن!", show_alert=True)
        return
    
    current_time = int(time.time())
    last_miner = user[10]
    miner_level = user[9]
    
    # چک کردن زمان
    if last_miner > 0 and (current_time - last_miner) < 3600:
        remaining = 3600 - (current_time - last_miner)
        minutes = remaining // 60
        seconds = remaining % 60
        await callback.answer(f"⏳ {minutes} دقیقه و {seconds} ثانیه دیگر", show_alert=True)
        return
    
    # محاسبه درآمد
    income = miner_level * 100
    
    # بروزرسانی دیتابیس
    db.update_resource(user_id, "zp", income)
    
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET last_miner_time = ? WHERE user_id = ?', 
                  (current_time, user_id))
    conn.commit()
    conn.close()
    
    # دریافت اطلاعات جدید
    user = db.get_user(user_id)
    
    text = f"""
⛏️ **برداشت موفق!**

💰 **درآمد:** +{income} ZP
📊 **کل ZP:** {user[5]:,}
🔧 **ماینر:** سطح {miner_level}
⏰ **برداشت بعدی:** 1 ساعت دیگر

⚡ برای درآمد بیشتر ماینر را ارتقا بده!
"""
    
    await callback.message.edit_text(text, reply_markup=get_back_keyboard())
    await callback.answer("✅ ZP برداشت شد!")

@dp.callback_query(F.data == "miner_upgrade")
async def upgrade_miner(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await callback.answer("⚠️ ابتدا ثبت‌نام کن!", show_alert=True)
        return
    
    miner_level = user[9]
    upgrade_cost = miner_level * 150
    
    if user[3] < upgrade_cost:
        await callback.answer(f"❌ سکه کافی نیست! نیاز: {upgrade_cost} سکه", show_alert=True)
        return
    
    # ارتقای ماینر
    db.update_resource(user_id, "coins", -upgrade_cost)
    
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET miner_level = miner_level + 1 WHERE user_id = ?', 
                  (user_id,))
    conn.commit()
    conn.close()
    
    # دریافت اطلاعات جدید
    user = db.get_user(user_id)
    
    text = f"""
⬆️ **ارتقای موفق!**

✅ ماینر به سطح {user[9]} ارتقا یافت!
💰 هزینه: {upgrade_cost} سکه
💎 باقی‌مانده: {user[3]:,} سکه
📈 درآمد جدید: {user[9] * 100} ZP/ساعت

🎉 حالا درآمد بیشتری داری!
"""
    
    await callback.message.edit_text(text, reply_markup=get_back_keyboard())
    await callback.answer("✅ ماینر ارتقا یافت!")

# ==================== DEFENSE HANDLERS ====================
@dp.callback_query(F.data == "defense_status")
async def defense_status(callback: CallbackQuery):
    user = db.get_user(callback.from_user.id)
    
    if user:
        defense_level = user[8]
        
        text = f"""
🛡️ **وضعیت پدافند پایگاه**

📊 **سطح کلی پدافند:** {defense_level}
🛡️ **کاهش damage:** {defense_level * 5}%

🏰 **سیستم‌های دفاعی:**
• برج سایبری: سطح {max(1, defense_level // 3)}
• موشک دفاعی: سطح {max(1, defense_level // 2)}
• ضد جنگنده: سطح {max(1, defense_level // 4)}

💰 **ارتقای بعدی:** {defense_level * 300} سکه
"""
    else:
        text = "⚠️ ابتدا ثبت‌نام کن!"
    
    await callback.message.edit_text(text, reply_markup=get_back_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "defense_cyber")
async def upgrade_cyber(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await callback.answer("⚠️ ابتدا ثبت‌نام کن!", show_alert=True)
        return
    
    defense_level = user[8]
    upgrade_cost = defense_level * 300
    
    if user[3] < upgrade_cost:
        await callback.answer(f"❌ سکه کافی نیست! نیاز: {upgrade_cost} سکه", show_alert=True)
        return
    
    # ارتقای پدافند
    db.update_resource(user_id, "coins", -upgrade_cost)
    
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET defense_level = defense_level + 1 WHERE user_id = ?', 
                  (user_id,))
    conn.commit()
    conn.close()
    
    user = db.get_user(user_id)
    
    text = f"""
🛡️ **برج سایبری ارتقا یافت!**

✅ سطح پدافند: {user[8]}
💰 هزینه: {upgrade_cost} سکه
💎 باقی‌مانده: {user[3]:,} سکه
🛡️ **کاهش damage جدید:** {user[8] * 5}%

✨ دفاع پایگاه تقویت شد!
"""
    
    await callback.message.edit_text(text, reply_markup=get_back_keyboard())
    await callback.answer("✅ پدافند ارتقا یافت!")

# ==================== BOX HANDLERS ====================
@dp.callback_query(F.data == "box_coin")
async def open_coin_box(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await callback.answer("⚠️ ابتدا ثبت‌نام کن!", show_alert=True)
        return
    
    box_price = 1000
    
    if user[3] < box_price:
        await callback.answer(f"❌ سکه کافی نیست! نیاز: {box_price} سکه", show_alert=True)
        return
    
    # خرید باکس
    db.update_resource(user_id, "coins", -box_price)
    
    # جایزه تصادفی
    reward = random.randint(200, 2000)
    db.update_resource(user_id, "coins", reward)
    
    user = db.get_user(user_id)
    
    text = f"""
🎁 **باکس سکه باز شد!**

💰 **جایزه:** {reward:,} سکه!
🎰 **شانس:** متوسط

💎 **موجودی جدید:**
• سکه: {user[3]:,}
• جم: {user[4]:,}

✨ شانس خود را دوباره امتحان کن!
"""
    
    await callback.message.edit_text(text, reply_markup=get_back_keyboard())
    await callback.answer("🎉 باکس باز شد!")

@dp.callback_query(F.data == "box_gem")
async def open_gem_box(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await callback.answer("⚠️ ابتدا ثبت‌نام کن!", show_alert=True)
        return
    
    box_price = 1500
    
    if user[3] < box_price:
        await callback.answer(f"❌ سکه کافی نیست! نیاز: {box_price} سکه", show_alert=True)
        return
    
    # خرید باکس
    db.update_resource(user_id, "coins", -box_price)
    
    # جایزه تصادفی (شانس 40% برای جم)
    if random.random() < 0.4:
        reward = random.randint(1, 5)
        db.update_resource(user_id, "gems", reward)
        reward_text = f"💎 **{reward} جم**"
        reward_type = "جم"
    else:
        reward = random.randint(300, 1000)
        db.update_resource(user_id, "coins", reward)
        reward_text = f"💰 **{reward:,} سکه**"
        reward_type = "سکه"
    
    user = db.get_user(user_id)
    
    text = f"""
🎁 **باکس جم باز شد!**

{reward_text}
🎰 **شانس:** {'عالی' if reward_type == 'جم' else 'خوب'}

💎 **موجودی جدید:**
• سکه: {user[3]:,}
• جم: {user[4]:,}

✨ {'💎 جم کمیاب!' if reward_type == 'جم' else 'دفعه بعد شانس بیشتری داری!'}
"""
    
    await callback.message.edit_text(text, reply_markup=get_back_keyboard())
    await callback.answer("🎉 باکس باز شد!")

# ==================== ATTACK HANDLERS ====================
@dp.callback_query(F.data == "attack_fast")
async def fast_attack(callback: CallbackQuery):
    if callback.message.reply_to_message is None:
        await callback.answer("❌ روی پیام کاربر ریپلای کن!", show_alert=True)
        return
    
    attacker_id = callback.from_user.id
    target_id = callback.message.reply_to_message.from_user.id
    
    if attacker_id == target_id:
        await callback.answer("❌ نمی‌توانی به خودت حمله کنی!", show_alert=True)
        return
    
    attacker = db.get_user(attacker_id)
    target = db.get_user(target_id)
    
    if not attacker or not target:
        await callback.answer("❌ کاربر یافت نشد!", show_alert=True)
        return
    
    # چک کردن موشک
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT missile_type, quantity FROM missiles WHERE user_id = ? AND quantity > 0 LIMIT 1', 
                  (attacker_id,))
    missile = cursor.fetchone()
    
    if not missile:
        await callback.answer("❌ موشک ندارید!", show_alert=True)
        conn.close()
        return
    
    missile_type = missile[0]
    
    # محاسبه damage
    base_damage = random.randint(50, 150)
    attacker_level = attacker[6]
    target_level = target[6]
    target_defense = target[8]
    
    # اعمال bonus/penalty
    level_diff = attacker_level - target_level
    level_bonus = 1 + (level_diff * 0.1)
    defense_reduction = 1 - (target_defense * 0.05)
    
    final_damage = int(base_damage * level_bonus * defense_reduction)
    
    # اعمال damage
    new_target_zp = max(0, target[5] - final_damage)
    damage_dealt = target[5] - new_target_zp
    
    db.update_resource(target_id, "zp", -damage_dealt)
    
    # XP برای حمله کننده
    xp_gain = min(50, damage_dealt // 5)
    db.update_resource(attacker_id, "xp", xp_gain)
    
    # کم کردن موشک
    cursor.execute('UPDATE missiles SET quantity = quantity - 1 WHERE user_id = ? AND missile_type = ?', 
                  (attacker_id, missile_type))
    
    # ثبت حمله
    cursor.execute('''
        INSERT INTO attacks (attacker_id, target_id, damage, missile_type)
        VALUES (?, ?, ?, ?)
    ''', (attacker_id, target_id, damage_dealt, missile_type))
    
    conn.commit()
    conn.close()
    
    # چک کردن ارتقا سطح
    attacker = db.get_user(attacker_id)
    if attacker[7] >= 1000:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET level = level + 1, xp = 0 WHERE user_id = ?', (attacker_id,))
        conn.commit()
        conn.close()
        level_up = True
    else:
        level_up = False
    
    text = f"""
⚔️ **حمله سریع انجام شد!**

🎯 **هدف:** {callback.message.reply_to_message.from_user.full_name}
💣 **موشک:** {missile_type}
⚡ **Damage:** {damage_dealt}
⭐ **XP کسب شده:** +{xp_gain}
🛡️ **دفاع هدف:** -{target_defense * 5}%

{"🎉 **سطح شما ارتقا یافت!**" if level_up else ""}
"""
    
    await callback.message.edit_text(text, reply_markup=get_back_keyboard())
    await callback.answer("✅ حمله انجام شد!")

# ==================== SUPPORT HANDLERS ====================
@dp.callback_query(F.data == "contact_admin")
async def contact_admin(callback: CallbackQuery):
    text = f"""
📩 **تماس با ادمین**

برای تماس با ادمین پیام خود را به صورت زیر بنویسید:

`@{DEVELOPER_ID} پیام شما`

👨‍💻 **توسعه‌دهنده:** @{DEVELOPER_ID}
⏰ **پاسخگویی:** 24 ساعته

💬 **مثال:**
`@{DEVELOPER_ID} سلام، یک باگ در سیستم حمله وجود داره`
"""
    
    await callback.message.edit_text(text, reply_markup=get_back_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "report_bug")
async def report_bug(callback: CallbackQuery):
    text = """
🆘 **گزارش باگ**

برای گزارش باگ لطفاً موارد زیر را ذکر کنید:

1. **شرح مشکل:** دقیقاً چه اتفاقی افتاده؟
2. **مراحل تولید:** چگونه باگ را تکرار کنیم؟
3. **عکس/ویدئو:** اگر ممکن است ارسال کنید
4. **سیستم:** موبایل/کامپیوتر، مرورگر/اپ

📧 **ارسال به:** @{DEVELOPER_ID}

⚠️ **توجه:** گزارش‌های دقیق تر سریع‌تر رفع می‌شوند!
"""
    
    text = text.replace("{DEVELOPER_ID}", DEVELOPER_ID)
    
    await callback.message.edit_text(text, reply_markup=get_back_keyboard())
    await callback.answer()

# ==================== ADMIN COMMANDS ====================
@dp.message(Command("admin"))
async def admin_panel(message: Message):
    user_id = message.from_user.id
    
    if str(user_id) != DEVELOPER_ID:
        await message.answer("⛔ دسترسی ممنوع!")
        return
    
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    conn.close()
    
    text = f"""
🔐 **پنل مدیریت ادمین**

👨‍💻 **توسعه‌دهنده:** @{DEVELOPER_ID}
👥 **کاربران:** {total_users}
🕒 **زمان:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📋 **دستورات:**
`/gift <آیدی> <نوع> <مقدار>` - هدیه دادن
`/addcoins <آیدی> <مقدار>` - افزودن سکه
`/addgems <آیدی> <مقدار>` - افزودن جم
`/status` - وضعیت ربات
`/backup` - ایجاد Backup
"""
    await message.answer(text)

@dp.message(Command("gift"))
async def gift_command(message: Message):
    user_id = message.from_user.id
    
    if str(user_id) != DEVELOPER_ID:
        await message.answer("⛔ فقط ادمین!")
        return
    
    parts = message.text.split()
    if len(parts) != 4:
        await message.answer("فرمت: /gift <آیدی> <coins|gems|zp> <مقدار>")
        return
    
    try:
        target_id = int(parts[1])
        resource_type = parts[2].lower()
        amount = int(parts[3])
        
        if resource_type == "coins":
            db.update_resource(target_id, "coins", amount)
            resource_name = "سکه"
            emoji = "💰"
        elif resource_type == "gems":
            db.update_resource(target_id, "gems", amount)
            resource_name = "جم"
            emoji = "💎"
        elif resource_type == "zp":
            db.update_resource(target_id, "zp", amount)
            resource_name = "ZP"
            emoji = "🎯"
        else:
            await message.answer("❌ نوع نامعتبر!")
            return
        
        await message.answer(f"""
✅ **هدیه ارسال شد!**

{emoji} **{amount:,} {resource_name}**
👤 **به کاربر:** {target_id}
👨‍💼 **توسط:** {message.from_user.full_name}
""")
        
    except ValueError:
        await message.answer("❌ مقدار نامعتبر!")
    except Exception as e:
        await message.answer(f"❌ خطا: {e}")

# ==================== MAIN FUNCTION ====================
async def main():
    logger.info("🚀 Starting Warzone Bot...")
    
    try:
        bot_info = await bot.get_me()
        logger.info(f"✅ Bot connected: @{bot_info.username}")
    except Exception as e:
        logger.error(f"❌ Connection failed: {e}")
        return
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
