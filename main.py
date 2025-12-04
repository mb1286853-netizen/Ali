"""
🏆 Warzone Bot - Main File (ساده‌شده برای Railway)
"""

import asyncio
import logging
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

# تنظیمات logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

# ==================== DATABASE (همان فایل) ====================
import sqlite3

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
                zone_coin INTEGER DEFAULT 1000,
                zone_gem INTEGER DEFAULT 0,
                zone_point INTEGER DEFAULT 500,
                level INTEGER DEFAULT 1,
                xp INTEGER DEFAULT 0,
                is_admin BOOLEAN DEFAULT 0,
                miner_level INTEGER DEFAULT 1,
                last_miner_claim INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_missiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                missile_name TEXT,
                quantity INTEGER DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ Database setup complete")
    
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
    
    def update_coins(self, user_id, amount):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET zone_coin = zone_coin + ? WHERE user_id = ?', 
                      (amount, user_id))
        conn.commit()
        conn.close()
    
    def update_gems(self, user_id, amount):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET zone_gem = zone_gem + ? WHERE user_id = ?', 
                      (amount, user_id))
        conn.commit()
        conn.close()
    
    def update_zp(self, user_id, amount):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET zone_point = zone_point + ? WHERE user_id = ?', 
                      (amount, user_id))
        conn.commit()
        conn.close()
    
    def get_user_missiles(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT missile_name, quantity FROM user_missiles WHERE user_id = ?', 
                      (user_id,))
        missiles = cursor.fetchall()
        conn.close()
        return missiles
    
    def add_missile(self, user_id, missile_name, quantity=1):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO user_missiles (user_id, missile_name, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, missile_name) 
            DO UPDATE SET quantity = quantity + ?
        ''', (user_id, missile_name, quantity, quantity))
        conn.commit()
        conn.close()

# ==================== KEYBOARDS ====================
def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎮 پنل جنگجو")],
            [KeyboardButton(text="🏦 بازار جنگ"), KeyboardButton(text="⛏️ معدن‌چی")],
            [KeyboardButton(text="🔧 سیستم ترکیب"), KeyboardButton(text="⚔️ حمله")],
            [KeyboardButton(text="📊 آمار من"), KeyboardButton(text="ℹ️ راهنما")]
        ],
        resize_keyboard=True
    )

def get_warrior_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💰 کیف پول", callback_data="wallet")],
            [InlineKeyboardButton(text="🚀 زرادخانه", callback_data="arsenal")],
            [InlineKeyboardButton(text="⬅️ بازگشت", callback_data="main_menu")]
        ]
    )

def get_market_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔥 موشک سریع", callback_data="market_fast")],
            [InlineKeyboardButton(text="💀 موشک آخرالزمانی", callback_data="market_apocalypse")],
            [InlineKeyboardButton(text="⬅️ بازگشت", callback_data="main_menu")]
        ]
    )

def get_miner_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⛏️ برداشت ZP", callback_data="miner_claim")],
            [InlineKeyboardButton(text="⬆️ ارتقای ماینر", callback_data="miner_upgrade")],
            [InlineKeyboardButton(text="⬅️ بازگشت", callback_data="main_menu")]
        ]
    )

def get_back_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ بازگشت", callback_data="main_menu")]
        ]
    )

# ==================== INITIALIZE ====================
bot = Bot(token=TOKEN)
dp = Dispatcher()
db = Database()

# ==================== ALL HANDLERS IN ONE FILE ====================

# ----- START HANDLERS -----
@dp.message(CommandStart())
async def start_command(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "ندارد"
    full_name = message.from_user.full_name
    
    db.create_user(user_id, username, full_name)
    
    text = f"""
🎮 به Warzone خوش آمدی، {full_name}!

📊 وضعیت اولیه:
💰 سکه: 1,000
💎 جم: 0 (فقط از ادمین)
🎯 ZP: 500

🔧 از کیبورد پایین استفاده کن!
"""
    await message.answer(text, reply_markup=get_main_keyboard())

@dp.message(F.text == "🎮 پنل جنگجو")
async def warrior_panel(message: Message):
    text = """
🎮 **پنل جنگجو**

در این بخش می‌توانی:
• کیف پول خود را ببینی
• زرادخانه موشک‌ها را مدیریت کنی
"""
    await message.answer(text, reply_markup=get_warrior_keyboard())

@dp.message(F.text == "🏦 بازار جنگ")
async def market_panel(message: Message):
    text = """
🏦 **بازار جنگ**

💎 **توجه:** کاربران عادی جم ندارند!

🔥 **موشک‌های سریع:** فقط با سکه
💀 **موشک‌های آخرالزمانی:** سکه + جم
"""
    await message.answer(text, reply_markup=get_market_keyboard())

@dp.message(F.text == "⛏️ معدن‌چی")
async def miner_panel(message: Message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if user:
        miner_level = user[10]
        income = miner_level * 100
        
        text = f"""
⛏️ **معدن‌چی ZP**

📊 **وضعیت:**
• سطح ماینر: {miner_level}
• درآمد ساعتی: {income} ZP
• برداشت: هر 1 ساعت
"""
    else:
        text = "⚠️ ابتدا با /start ثبت‌نام کن!"
    
    await message.answer(text, reply_markup=get_miner_keyboard())

# ----- CALLBACK HANDLERS -----
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

🪙 سکه: {user[3]:,}
💎 جم: {user[4]:,}
🎯 ZP: {user[5]:,}
"""
    else:
        text = "⚠️ ابتدا ثبت‌نام کن!"
    
    await callback.message.edit_text(text, reply_markup=get_back_keyboard())
    await callback.answer()

# ----- MARKET HANDLERS -----
MISSILES = {
    "fast": [
        {"name": "شهاب (Meteor)", "damage": 50, "price": 200, "level": 1},
        {"name": "تگرگ (Hailstorm)", "damage": 70, "price": 500, "level": 2},
        {"name": "سیل (Torrent)", "damage": 90, "price": 1000, "level": 3},
    ]
}

@dp.callback_query(F.data == "market_fast")
async def show_fast_missiles(callback: CallbackQuery):
    text = "🔥 **موشک‌های سریع**\n\n"
    
    buttons = []
    for missile in MISSILES["fast"]:
        btn_text = f"{missile['name']} - {missile['price']} سکه"
        btn_data = f"buy_fast_{missile['name']}"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=btn_data)])
    
    buttons.append([InlineKeyboardButton(text="⬅️ بازگشت", callback_data="main_menu")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    for missile in MISSILES["fast"]:
        text += f"• **{missile['name']}**\n"
        text += f"  ⚡ Damage: {missile['damage']}\n"
        text += f"  💰 قیمت: {missile['price']} سکه\n\n"
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

# ----- MINER HANDLERS -----
import time

@dp.callback_query(F.data == "miner_claim")
async def claim_miner(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await callback.answer("⚠️ ابتدا ثبت‌نام کن!", show_alert=True)
        return
    
    current_time = int(time.time())
    last_claim = user[11]
    miner_level = user[10]
    
    if last_claim > 0 and (current_time - last_claim) < 3600:
        remaining = 3600 - (current_time - last_claim)
        minutes = remaining // 60
        await callback.answer(f"⏳ {minutes} دقیقه دیگر", show_alert=True)
        return
    
    income = miner_level * 100
    db.update_zp(user_id, income)
    
    # بروزرسانی زمان
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET last_miner_claim = ? WHERE user_id = ?', 
                  (current_time, user_id))
    conn.commit()
    conn.close()
    
    user = db.get_user(user_id)
    text = f"""
⛏️ **برداشت موفق!**

✅ **درآمد:** +{income} ZP
📊 **کل ZP:** {user[5]:,}
⏰ **برداشت بعدی:** 1 ساعت دیگر
"""
    
    await callback.message.edit_text(text, reply_markup=get_back_keyboard())
    await callback.answer("✅ برداشت شد!")

# ----- ADMIN COMMANDS -----
@dp.message(Command("admin"))
async def admin_panel(message: Message):
    user_id = message.from_user.id
    
    if str(user_id) != DEVELOPER_ID:
        await message.answer("⛔ دسترسی ممنوع!")
        return
    
    text = f"""
🔐 **پنل ادمین**

👨‍💻 شما ادمین هستید!

📋 **دستورات:**
/gift <آیدی> <نوع> <مقدار>
/status - وضعیت ربات
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
        await message.answer("فرمت: /gift <آیدی> <coin|gem|zp> <مقدار>")
        return
    
    try:
        target_id = int(parts[1])
        resource_type = parts[2].lower()
        amount = int(parts[3])
        
        if resource_type == "coin":
            db.update_coins(target_id, amount)
            resource_name = "سکه"
        elif resource_type == "gem":
            db.update_gems(target_id, amount)
            resource_name = "جم"
        elif resource_type == "zp":
            db.update_zp(target_id, amount)
            resource_name = "ZP"
        else:
            await message.answer("❌ نوع نامعتبر!")
            return
        
        await message.answer(f"✅ {amount} {resource_name} به کاربر {target_id} داده شد!")
        
    except:
        await message.answer("❌ خطا!")

# ==================== MAIN FUNCTION ====================
async def main():
    logger.info("🚀 Starting Warzone Bot...")
    
    try:
        bot_info = await bot.get_me()
        logger.info(f"✅ Bot: @{bot_info.username}")
    except Exception as e:
        logger.error(f"❌ Connection failed: {e}")
        return
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
