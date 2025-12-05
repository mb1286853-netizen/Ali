"""
🏆 Warzone Bot - نسخه نهایی و کامل
تمامی مشکلات رفع شده
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
DEVELOPER_ID = int(os.getenv("DEVELOPER_ID", "0"))
ADMIN_IDS = [DEVELOPER_ID]  # شما ادمین اصلی هستید

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
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS missiles (
                user_id INTEGER,
                missile_type TEXT,
                quantity INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, missile_type)
            )
''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fighters (
                user_id INTEGER,
                fighter_type TEXT,
                quantity INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, fighter_type)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS support_tickets (
                ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                message TEXT,
                status TEXT DEFAULT 'open',
                admin_reply TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS free_boxes (
                user_id INTEGER PRIMARY KEY,
                last_free_box INTEGER DEFAULT 0,
                total_claimed INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attacks (
                attack_id INTEGER PRIMARY KEY AUTOINCREMENT,
                attacker_id INTEGER,
                target_id INTEGER,
                damage INTEGER,
                missile_type TEXT,
                combo_type TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            [InlineKeyboardButton(text="🎁 باکس رایگان (24h)", callback_data="box_free")],
            [InlineKeyboardButton(text="⬅️ بازگشت", callback_data="main_menu")]
        ]
    )

def get_support_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📩 ایجاد تیکت", callback_data="create_ticket")],
            [InlineKeyboardButton(text="📋 تیکت‌های من", callback_data="my_tickets")],
            [InlineKeyboardButton(text="📜 قوانین", callback_data="support_rules")],
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
    {"name": "موشک هوا به هوا", "price": 1500, "damage": 150, "level": 4},
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
    
    cursor.execute('SELECT missile_type, quantity FROM missiles WHERE user_id = ? AND missile_type = "موشک هوا به هوا"', (user_id,))
    air_missiles = cursor.fetchall()
    
    conn.close()
    
    text = "🛩️ **ناوگان جنگنده‌های شما**\n\n"
    
    if user_fighters:
        text += "**✈️ جنگنده‌ها:**\n"
        for fighter in user_fighters:
            f_type, quantity = fighter
            text += f"• {f_type}: {quantity} عدد\n"
        text += "\n"
    else:
        text += "📭 **هنوز جنگنده ندارید!**\n\n"
    
    if air_missiles:
        text += "**🚀 موشک‌های هوا به هوا:**\n"
        for missile in air_missiles:
            m_type, quantity = missile
            text += f"• {m_type}: {quantity} عدد\n"
    else:
        text += "📭 **موشک هوا به هوا ندارید!**\n\n"
    
    text += "\n🏪 برای خرید به بازار جنگ بروید!"
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏪 خرید جنگنده", callback_data="market_fighters")],
            [InlineKeyboardButton(text="🚀 خرید موشک هوا به هوا", callback_data="buy_air_missile")],
            [InlineKeyboardButton(text="⬅️ بازگشت", callback_data="main_menu")]
        ]
    )
    
    await message.answer(text, reply_markup=keyboard)

@dp.message(F.text == "🎁 باکس‌ها")
async def boxes_panel(message: Message):
    text = """
🎁 **باکس‌های شگفت‌انگیز**

شانس خود را برای بردن جوایز عالی امتحان کن:

📦 **باکس سکه:** 1000 سکه - جایزه: 200-2000 سکه
💎 **باکس جم:** 1500 سکه - جایزه: 1-5 جم  
🎯 **باکس ZP:** 2000 سکه - جایزه: 100-500 ZP
🎁 **باکس رایگان:** هر 24 ساعت - جایزه: تصادفی

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
    text = """
📞 **سیستم تیکت پشتیبانی**

🎫 **برای ایجاد تیکت جدید:**
1. روی "📩 ایجاد تیکت" کلیک کن
2. پیام خودت رو بنویس
3. تیکت ثبت می‌شه

📋 **تیکت‌های من:**
می‌تونی تیکت‌های قبلیت رو ببینی و وضعشون رو چک کنی

⚠️ **قوانین:** احترام متقابل، عدم اسپم
⏰ **پاسخگویی:** 24 ساعته
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

@dp.callback_query(F.data == "stats")
async def show_stats(callback: CallbackQuery):
    user = db.get_user(callback.from_user.id)
    
    if not user:
        await callback.answer("⚠️ ابتدا ثبت‌نام کن!", show_alert=True)
        return
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT SUM(quantity) FROM missiles WHERE user_id = ?', (user[0],))
    total_missiles = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT SUM(quantity) FROM fighters WHERE user_id = ?', (user[0],))
    total_fighters = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT COUNT(*) FROM attacks WHERE attacker_id = ?', (user[0],))
    total_attacks = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT COUNT(*) FROM attacks WHERE target_id = ?', (user[0],))
    total_defended = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT COUNT(*) FROM users WHERE zp > ?', (user[5],))
    rank = cursor.fetchone()[0] + 1
    
    conn.close()
    
    text = f"""
📊 **آمار کامل شما**

👤 **اطلاعات:**
• نام: {user[2]}
• سطح: {user
