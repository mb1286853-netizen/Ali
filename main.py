#!/usr/bin/env python3
"""
Warzone Telegram Bot - Version 2.0.0
ربات جنگی کامل - بدون باگ
"""

import asyncio
import sqlite3
import random
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup,
    InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
import aiohttp
from aiohttp import web

# === تنظیمات لاگ ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# === بارگذاری متغیرهای محیطی ===
load_dotenv()

# === تنظیمات ===
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = [int(x.strip()) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip()]
PORT = int(os.getenv('PORT', 8080))
KEEP_ALIVE_URL = os.getenv('KEEP_ALIVE_URL', '')

if not BOT_TOKEN:
    raise ValueError("لطفا BOT_TOKEN را در .env تنظیم کنید")

# === راه‌اندازی ربات ===
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
# === States برای FSM ===
class UserStates(StatesGroup):
    waiting_for_attack = State()
    waiting_for_target_reply = State()
    waiting_for_gift_amount = State()
    waiting_for_broadcast = State()
    admin_panel = State()

# === کلاس دیتابیس ===
class Database:
    def __init__(self, db_path='app/data/warzone.db'):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # جدول کاربران
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            zone_coin INTEGER DEFAULT 1000,
            zone_gem INTEGER DEFAULT 10,
            zone_point INTEGER DEFAULT 500,
            level INTEGER DEFAULT 1,
            xp INTEGER DEFAULT 0,
            is_admin BOOLEAN DEFAULT 0,
            miner_level INTEGER DEFAULT 1,
            last_miner_claim INTEGER,
            cyber_tower_level INTEGER DEFAULT 0,
            defense_missile_level INTEGER DEFAULT 0,
            defense_electronic_level INTEGER DEFAULT 0,
            defense_antifighter_level INTEGER DEFAULT 0,
            total_defense_bonus REAL DEFAULT 0.0,
            created_at INTEGER DEFAULT (strftime('%s', 'now'))
        )
        ''')
        
        # جدول موشک‌ها
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_missiles (
            user_id INTEGER,
            missile_name TEXT,
            quantity INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, missile_name),
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        ''')
        
        # جدول حمله‌ها
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS attacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attacker_id INTEGER,
            target_id INTEGER,
            attack_type TEXT,
            damage INTEGER,
            loot_coins INTEGER,
            loot_gems INTEGER,
            timestamp INTEGER DEFAULT (strftime('%s', 'now')),
            FOREIGN KEY (attacker_id) REFERENCES users(user_id),
            FOREIGN KEY (target_id) REFERENCES users(user_id)
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def register_user(self, user_id: int, username: str, full_name: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username, full_name) 
        VALUES (?, ?, ?)
        ''', (user_id, username, full_name))
        
        # تنظیم ادمین اگر در لیست باشد
        if user_id in ADMIN_IDS:
            cursor.execute('UPDATE users SET is_admin = 1 WHERE user_id = ?', (user_id,))
        
        # مقدار اولیه موشک‌ها
        initial_missiles = [
            (user_id, 'موشک کوتاه برد', 5),
            (user_id, 'موشک میان برد', 3),
            (user_id, 'موشک بالستیک', 1)
        ]
        
        for missile in initial_missiles:
            cursor.execute('''
            INSERT OR IGNORE INTO user_missiles (user_id, missile_name, quantity)
            VALUES (?, ?, ?)
            ''', missile)
        
        conn.commit()
        conn.close()
    
    def get_user(self, user_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
        return dict(user) if user else None
    
    def get_user_missiles(self, user_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        SELECT missile_name, quantity FROM user_missiles 
        WHERE user_id = ? AND quantity > 0
        ORDER BY 
            CASE missile_name
                WHEN 'موشک کوتاه برد' THEN 1
                WHEN 'موشک میان برد' THEN 2
                WHEN 'موشک بالستیک' THEN 3
                WHEN 'موشک هدایت شونده' THEN 4
                WHEN 'موشک زمین به هوا' THEN 5
                WHEN 'موشک زلزله' THEN 6
                WHEN 'موشک سونامی' THEN 7
                WHEN 'موشک خورشیدی' THEN 8
                WHEN 'موشک پلاسمایی' THEN 9
                WHEN 'موشک هسته‌ای' THEN 10
                ELSE 11
            END
        ''', (user_id,))
        missiles = cursor.fetchall()
        conn.close()
        return [dict(m) for m in missiles]
    
    def update_user_coins(self, user_id: int, amount: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        UPDATE users 
        SET zone_coin = zone_coin + ? 
        WHERE user_id = ?
        ''', (amount, user_id))
        conn.commit()
        conn.close()
    
    def update_user_gems(self, user_id: int, amount: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        UPDATE users 
        SET zone_gem = zone_gem + ? 
        WHERE user_id = ?
        ''', (amount, user_id))
        conn.commit()
        conn.close()
    
    def update_user_zp(self, user_id: int, amount: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        UPDATE users 
        SET zone_point = zone_point + ? 
        WHERE user_id = ?
        ''', (amount, user_id))
        conn.commit()
        conn.close()
    
    def add_xp(self, user_id: int, xp_amount: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT xp, level FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        
        if user:
            current_xp = user['xp'] + xp_amount
            level = user['level']
            xp_needed = level * 100
            
            if current_xp >= xp_needed:
                new_level = level + 1
                remaining_xp = current_xp - xp_needed
                cursor.execute('''
                UPDATE users 
                SET xp = ?, level = ?, zone_coin = zone_coin + 1000, zone_gem = zone_gem + 5
                WHERE user_id = ?
                ''', (remaining_xp, new_level, user_id))
                level_up = True
            else:
                cursor.execute('UPDATE users SET xp = ? WHERE user_id = ?', (current_xp, user_id))
                level_up = False
            
            conn.commit()
            conn.close()
            return level_up, new_level if level_up else level
        return False, user['level'] if user else 1
    
    def get_all_users(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, username, full_name FROM users')
        users = cursor.fetchall()
        conn.close()
        return [dict(u) for u in users]
    
    def get_top_users(self, limit=10):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        SELECT user_id, username, full_name, zone_coin, zone_gem, zone_point, level
        FROM users 
        ORDER BY zone_coin DESC 
        LIMIT ?
        ''', (limit,))
        users = cursor.fetchall()
        conn.close()
        return [dict(u) for u in users]
        # === راه‌اندازی دیتابیس ===
db = Database()

# === داده‌های بازی ===
MISSILE_DATA = {
    'موشک کوتاه برد': {'damage': 50, 'price': 200, 'min_level': 1, 'type': 'normal'},
    'موشک میان برد': {'damage': 70, 'price': 500, 'min_level': 2, 'type': 'normal'},
    'موشک بالستیک': {'damage': 90, 'price': 1000, 'min_level': 3, 'type': 'normal'},
    'موشک هدایت شونده': {'damage': 110, 'price': 2000, 'min_level': 4, 'type': 'normal'},
    'موشک زمین به هوا': {'damage': 130, 'price': 5000, 'min_level': 5, 'type': 'normal'},
    'موشک زلزله': {'damage': 250, 'price': 25000, 'min_level': 6, 'type': 'special', 'gem_cost': 1},
    'موشک سونامی': {'damage': 300, 'price': 30000, 'min_level': 7, 'type': 'special', 'gem_cost': 2},
    'موشک خورشیدی': {'damage': 350, 'price': 35000, 'min_level': 8, 'type': 'special', 'gem_cost': 3},
    'موشک پلاسمایی': {'damage': 400, 'price': 40000, 'min_level': 9, 'type': 'special', 'gem_cost': 4},
    'موشک هسته‌ای': {'damage': 500, 'price': 50000, 'min_level': 10, 'type': 'special', 'gem_cost': 5}
}

ATTACK_COMBOS = {
    'حمله ساده': {
        'multiplier': 1.0,
        'requirements': {'موشک کوتاه برد': 1},
        'min_level': 1,
        'description': 'نیاز: 1 موشک کوتاه برد'
    },
    'حمله متوسط': {
        'multiplier': 1.5,
        'requirements': {'موشک میان برد': 1},
        'min_level': 2,
        'description': 'نیاز: 1 موشک میان برد'
    },
    'حمله پیشرفته': {
        'multiplier': 2.0,
        'requirements': {'موشک بالستیک': 1},
        'min_level': 3,
        'description': 'نیاز: 1 موشک بالستیک'
    },
    'حمله ویرانگر': {
        'multiplier': 5.0,
        'requirements': {'موشک هسته‌ای': 1, 'zone_gem': 10},
        'min_level': 10,
        'description': 'نیاز: 1 موشک هسته‌ای + 10 جم'
    }
}

MINER_LEVELS = {
    1: {'zp_per_hour': 100, 'upgrade_cost': 100},
    2: {'zp_per_hour': 200, 'upgrade_cost': 200},
    3: {'zp_per_hour': 300, 'upgrade_cost': 300},
    4: {'zp_per_hour': 400, 'upgrade_cost': 400},
    5: {'zp_per_hour': 500, 'upgrade_cost': 500},
    6: {'zp_per_hour': 600, 'upgrade_cost': 600},
    7: {'zp_per_hour': 700, 'upgrade_cost': 700},
    8: {'zp_per_hour': 800, 'upgrade_cost': 800},
    9: {'zp_per_hour': 900, 'upgrade_cost': 900},
    10: {'zp_per_hour': 1000, 'upgrade_cost': 10000},
    11: {'zp_per_hour': 1100, 'upgrade_cost': 11000},
    12: {'zp_per_hour': 1200, 'upgrade_cost': 12000},
    13: {'zp_per_hour': 1300, 'upgrade_cost': 13000},
    14: {'zp_per_hour': 1400, 'upgrade_cost': 14000},
    15: {'zp_per_hour': 1500, 'upgrade_cost': 50000}
}

# === توابع کمکی ===
def create_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 پروفایل"), KeyboardButton(text="⚔️ حمله")],
            [KeyboardButton(text="🏪 بازار"), KeyboardButton(text="🎁 باکس")],
            [KeyboardButton(text="⛏️ ماینر"), KeyboardButton(text="🏰 دفاع")],
            [KeyboardButton(text="📊 رنکینگ"), KeyboardButton(text="📖 راهنما")]
        ],
        resize_keyboard=True,
        input_field_placeholder="انتخاب کنید..."
    )
    return keyboard

def create_admin_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👑 پنل ادمین")],
            [KeyboardButton(text="📊 آمار کامل"), KeyboardButton(text="📢 پیام همگانی")],
            [KeyboardButton(text="🎁 هدیه همگانی"), KeyboardButton(text="➕ سکه")],
            [KeyboardButton(text="💎 جم"), KeyboardButton(text="⚡ ZP")],
            [KeyboardButton(text="📈 تغییر لول"), KeyboardButton(text="🔙 بازگشت")]
        ],
        resize_keyboard=True,
        input_field_placeholder="دستور ادمین..."
    )
    return keyboard

def is_admin(user_id: int):
    """بررسی ادمین بودن کاربر"""
    return user_id in ADMIN_IDS

def get_defense_bonus(defense_levels):
    """محاسبه بانس دفاع"""
    total_bonus = 0
    total_bonus += defense_levels.get('missile', 0) * 0.05
    total_bonus += defense_levels.get('electronic', 0) * 0.03
    total_bonus += defense_levels.get('antifighter', 0) * 0.07
    return min(total_bonus, 0.5)  # حداکثر 50% بانس
# === هندلرهای اصلی ===
@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    full_name = message.from_user.full_name
    
    # ثبت کاربر
    db.register_user(user_id, username, full_name)
    
    welcome_text = f"""
🚀 <b>به جنگ‌افزار خوش آمدید {full_name}!</b>

🎮 <i>یک ربات جنگی کامل با قابلیت‌های:</i>
• ⚔️ سیستم حمله پیشرفته
• 🏪 بازار خرید موشک
• 🎁 باکس‌های مختلف
• ⛏️ سیستم ماینینگ
• 🏰 سیستم دفاع
• 📊 رنکینگ رقابتی

💰 دارایی اولیه:
• 1000 سکه
• 10 جم  
• 500 ZP
• 5 موشک کوتاه برد
• 3 موشک میان برد
• 1 موشک بالستیک

📖 برای شروع از دکمه‌های زیر استفاده کنید:
    """
    
    await message.answer(welcome_text, reply_markup=create_main_keyboard())

@dp.message(F.text == "👤 پروفایل")
async def cmd_profile(message: Message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await message.answer("❌ ابتدا با /start ثبت نام کنید!")
        return
    
    # محاسبه ZP قابل دریافت از ماینر
    miner_zp = 0
    if user['last_miner_claim']:
        time_passed = int(time.time()) - user['last_miner_claim']
        zp_per_hour = MINER_LEVELS[user['miner_level']]['zp_per_hour']
        miner_zp = int((time_passed / 3600) * zp_per_hour)
    
    # دریافت موشک‌ها
    missiles = db.get_user_missiles(user_id)
    missiles_text = ""
    if missiles:
        for missile in missiles[:5]:  # فقط 5 موشک اول
            missiles_text += f"• {missile['missile_name']}: {missile['quantity']}\n"
        if len(missiles) > 5:
            missiles_text += f"• و {len(missiles) - 5} موشک دیگر...\n"
    
    profile_text = f"""
📊 <b>پروفایل جنگ‌افزار</b>
━━━━━━━━━━━━━━
👤 نام: {user['full_name']}
🆔 آیدی: {user['user_id']}
🎯 لول: {user['level']}
⭐ XP: {user['xp']}/{user['level'] * 100}
━━━━━━━━━━━━━━
💰 سکه: {user['zone_coin']} ZC
💎 جم: {user['zone_gem']} ZG
⚡ امتیاز: {user['zone_point']} ZP
━━━━━━━━━━━━━━
⛏️ ماینر: لول {user['miner_level']}
📦 ZP قابل دریافت: {miner_zp}
━━━━━━━━━━━━━━
💣 موشک‌ها:
{missiles_text if missiles_text else "• هیچ موشکی ندارید!"}
━━━━━━━━━━━━━━
🏰 سیستم دفاع:
• 🚀 دفاع موشکی: لول {user['defense_missile_level']}
• 📡 جنگ الکترونیک: لول {user['defense_electronic_level']}
• ✈️ ضد جنگنده: لول {user['defense_antifighter_level']}
• 🛡️ بانس کلی: {user['total_defense_bonus']*100:.1f}%
━━━━━━━━━━━━━━
👑 وضعیت: {"🛡️ ادمین" if user['is_admin'] else "👤 کاربر عادی"}
📅 عضویت: {datetime.fromtimestamp(user['created_at']).strftime('%Y/%m/%d')}
    """
    
    await message.answer(profile_text)
    @dp.message(F.text == "⚔️ حمله")
async def cmd_attack(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await message.answer("❌ ابتدا با /start ثبت نام کنید!")
        return
    
    # ایجاد کیبورد برای انتخاب نوع حمله
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="حمله ساده (1x)", callback_data="attack_simple"),
            InlineKeyboardButton(text="حمله متوسط (1.5x)", callback_data="attack_medium")
        ],
        [
            InlineKeyboardButton(text="حمله پیشرفته (2x)", callback_data="attack_advanced"),
            InlineKeyboardButton(text="حمله ویرانگر (5x)", callback_data="attack_nuclear")
        ],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")]
    ])
    
    attack_info = """
⚔️ <b>انتخاب نوع حمله:</b>
━━━━━━━━━━━━━━
1. حمله ساده
   • ضریب: 1x
   • نیاز: 1 موشک کوتاه برد
   
2. حمله متوسط  
   • ضریب: 1.5x
   • نیاز: 1 موشک میان برد
   
3. حمله پیشرفته
   • ضریب: 2x
   • نیاز: 1 موشک بالستیک
   
4. حمله ویرانگر
   • ضریب: 5x
   • نیاز: 1 موشک هسته‌ای + 10 جم
    """
    
    await message.answer(attack_info, reply_markup=keyboard)

@dp.callback_query(F.data.startswith("attack_"))
async def process_attack_type(callback: CallbackQuery, state: FSMContext):
    attack_type = callback.data.replace("attack_", "")
    
    attack_map = {
        'simple': 'حمله ساده',
        'medium': 'حمله متوسط',
        'advanced': 'حمله پیشرفته',
        'nuclear': 'حمله ویرانگر'
    }
    
    attack_name = attack_map.get(attack_type)
    
    # ذخیره نوع حمله
    await state.update_data(attack_type=attack_type, attack_name=attack_name)
    await state.set_state(UserStates.waiting_for_target_reply)
    
    await callback.message.edit_text(f"""
🎯 <b>انتخاب هدف</b>
━━━━━━━━━━━━━━
نوع حمله: {attack_name}

📝 <b>روش حمله:</b>
1. روی پیام کاربر مورد نظر <b>ریپلای (Reply)</b> کنید
2. سپس دستور /attack را بنویسید

⚠️ نکته: فقط می‌توانید به کاربرانی حمله کنید که در ربات ثبت‌نام کرده‌اند.
    """)
    await callback.answer()

@dp.message(Command("attack"))
@dp.message(F.text == "/attack")
async def cmd_attack_reply(message: Message, state: FSMContext):
    """حمله با ریپلای"""
    
    # بررسی ریپلای
    if not message.reply_to_message:
        await message.answer("""
❌ <b>روش صحیح حمله:</b>
1. روی پیام کاربر مورد نظر <b>ریپلای (Reply)</b> کنید
2. سپس دستور /attack را بنویسید

⚠️ یا از منوی ⚔️ حمله استفاده کنید.
        """)
        return
    
    # دریافت اطلاعات حمله‌کننده
    attacker_id = message.from_user.id
    attacker = db.get_user(attacker_id)
    
    if not attacker:
        await message.answer("❌ ابتدا با /start ثبت نام کنید!")
        return
    
    # دریافت اطلاعات هدف از ریپلای
    target_user = message.reply_to_message.from_user
    target_id = target_user.id
    
    # بررسی حمله به خود
    if target_id == attacker_id:
        await message.answer("❌ نمی‌توانید به خود حمله کنید!")
        return
    
    # بررسی وجود هدف در دیتابیس
    target = db.get_user(target_id)
    if not target:
        await message.answer("❌ کاربر هدف در ربات ثبت‌نام نکرده است!")
        return
    
    # درخواست نوع حمله
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="حمله ساده", callback_data=f"quick_attack_simple_{target_id}"),
            InlineKeyboardButton(text="حمله متوسط", callback_data=f"quick_attack_medium_{target_id}")
        ],
        [
            InlineKeyboardButton(text="حمله پیشرفته", callback_data=f"quick_attack_advanced_{target_id}"),
            InlineKeyboardButton(text="حمله ویرانگر", callback_data=f"quick_attack_nuclear_{target_id}")
        ]
    ])
    
    await message.answer(f"""
🎯 <b>هدف انتخاب شد:</b>
━━━━━━━━━━━━━━
👤 نام: {target_user.full_name}
🆔 آیدی: {target_id}

📊 <b>انتخاب نوع حمله:</b>
    """, reply_markup=keyboard)

@dp.callback_query(F.data.startswith("quick_attack_"))
async def process_quick_attack(callback: CallbackQuery):
    """پردازش حمله سریع"""
    try:
        # استخراج اطلاعات از callback_data
        parts = callback.data.split("_")
        attack_type = parts[2]  # simple, medium, advanced, nuclear
        target_id = int(parts[3])
        
        attacker_id = callback.from_user.id
        
        # انجام حمله
        await execute_attack(attacker_id, target_id, attack_type, callback.message)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Quick attack error: {e}")
        await callback.answer("❌ خطا در انجام حمله!")

async def execute_attack(attacker_id: int, target_id: int, attack_type: str, message_obj):
    """انجام حمله"""
    attacker = db.get_user(attacker_id)
    target = db.get_user(target_id)
    
    if not attacker or not target:
        await message_obj.answer("❌ کاربر یافت نشد!")
        return
    
    # بررسی حمله به خود
    if attacker_id == target_id:
        await message_obj.answer("❌ نمی‌توانید به خود حمله کنید!")
        return
    
    # انتخاب combo
    combo_map = {
        'simple': ATTACK_COMBOS['حمله ساده'],
        'medium': ATTACK_COMBOS['حمله متوسط'],
        'advanced': ATTACK_COMBOS['حمله پیشرفته'],
        'nuclear': ATTACK_COMBOS['حمله ویرانگر']
    }
    
    combo = combo_map.get(attack_type)
    
    if not combo:
        await message_obj.answer("❌ نوع حمله نامعتبر!")
        return
    
    # بررسی سطح
    if attacker['level'] < combo['min_level']:
        await message_obj.answer(f"❌ برای این حمله حداقل لول {combo['min_level']} نیاز دارید!")
        return
    
    # بررسی نیازمندی‌ها
    for req, amount in combo['requirements'].items():
        if req in MISSILE_DATA:
            # بررسی موشک
            missiles = db.get_user_missiles(attacker_id)
            missile_qty = next((m['quantity'] for m in missiles if m['missile_name'] == req), 0)
            if missile_qty < amount:
                await message_obj.answer(f"❌ {req} کافی ندارید! (نیاز: {amount})")
                return
        elif req == 'zone_gem':
            if attacker['zone_gem'] < amount:
                await message_obj.answer(f"❌ جم کافی ندارید! (نیاز: {amount})")
                return
    
    # محاسبه خسارت با در نظر گرفتن دفاع
    base_damage = 100 + (attacker['level'] * 10)
    actual_damage = int(base_damage * combo['multiplier'] * (1 - target['total_defense_bonus']))
    
    # محاسبه غنیمت (حداکثر 15% از دارایی هدف)
    loot_coins = min(int(target['zone_coin'] * 0.15), 5000)
    loot_gems = min(int(target['zone_gem'] * 0.10), 50)
    
    # کسر منابع از هدف (حداقل صفر)
    new_target_coins = max(target['zone_coin'] - loot_coins, 0)
    new_target_gems = max(target['zone_gem'] - loot_gems, 0)
    
    db.update_user_coins(target_id, -loot_coins)
    db.update_user_gems(target_id, -loot_gems)
    
    # اضافه کردن منابع به حمله‌کننده
    db.update_user_coins(attacker_id, loot_coins)
    db.update_user_gems(attacker_id, loot_gems)
    
    # کسر موشک‌ها
    for req, amount in combo['requirements'].items():
        if req in MISSILE_DATA:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
            UPDATE user_missiles 
            SET quantity = quantity - ? 
            WHERE user_id = ? AND missile_name = ?
            ''', (amount, attacker_id, req))
            conn.commit()
            conn.close()
    
    # اضافه کردن XP
    level_up, new_level = db.add_xp(attacker_id, 50)
    
    # ارسال گزارش به حمله‌کننده
    attack_names = {
        'simple': 'حمله ساده',
        'medium': 'حمله متوسط',
        'advanced': 'حمله پیشرفته',
        'nuclear': 'حمله ویرانگر'
    }
    
    report_text = f"""
🎯 <b>حمله موفق!</b>
━━━━━━━━━━━━━━
⚔️ حمله‌کننده: {attacker['full_name']}
🎯 هدف: {target['full_name']}
💥 نوع حمله: {attack_names[attack_type]}
🛡️ کاهش بانس دفاع: {target['total_defense_bonus']*100:.1f}%
💢 خسارت وارد شده: {actual_damage}
━━━━━━━━━━━━━━
💰 غنیمت سکه: {loot_coins} ZC
💎 غنیمت جم: {loot_gems} ZG
━━━━━━━━━━━━━━
⭐ XP کسب شده: 50
{'🎉 سطح شما افزایش یافت!' if level_up else ''}
    """
    
    await message_obj.answer(report_text)
    
    # اطلاع به هدف
    try:
        target_report = f"""
🚨 <b>تحت حمله قرار گرفتید!</b>
━━━━━━━━━━━━━━
⚔️ حمله‌کننده: {attacker['full_name']}
💢 خسارت: {actual_damage}
💰 سکه از دست رفته: {loot_coins}
💎 جم از دست رفته: {loot_gems}
🛡️ دفاع شما {target['total_defense_bonus']*100:.1f}% خسارت را کاهش داد
📊 موجودی جدید:
• سکه: {new_target_coins} ZC
• جم: {new_target_gems} ZG
        """
        await bot.send_message(target_id, target_report)
    except Exception as e:
        logger.error(f"Failed to send attack report to target: {e}")
        # === داده‌های بازی با اسامی خلاقانه ===
MISSILE_DATA = {
    # موشک‌های معمولی
    'شبح (Ghost)': {'damage': 50, 'price': 200, 'min_level': 1, 'type': 'normal'},
    'رعد (Thunder)': {'damage': 70, 'price': 500, 'min_level': 2, 'type': 'normal'},
    'تندر (Boomer)': {'damage': 90, 'price': 1000, 'min_level': 3, 'type': 'normal'},
    'هاوک (Hawk)': {'damage': 110, 'price': 2000, 'min_level': 4, 'type': 'normal'},
    'پاتریوت (Patriot)': {'damage': 130, 'price': 5000, 'min_level': 5, 'type': 'normal'},
    
    # موشک‌های ویژه
    'شهاب (Meteor)': {'damage': 250, 'price': 25000, 'min_level': 6, 'type': 'special', 'gem_cost': 1},
    'سیل (Tsunami)': {'damage': 300, 'price': 30000, 'min_level': 7, 'type': 'special', 'gem_cost': 2},
    'توفان (Storm)': {'damage': 350, 'price': 35000, 'min_level': 8, 'type': 'special', 'gem_cost': 3},
    'تایفون (Typhoon)': {'damage': 400, 'price': 40000, 'min_level': 9, 'type': 'special', 'gem_cost': 4},
    'آپوکالیپس (Apocalypse)': {'damage': 500, 'price': 50000, 'min_level': 10, 'type': 'special', 'gem_cost': 5}
}

ATTACK_COMBOS = {
    'حمله سریع': {
        'multiplier': 1.0,
        'requirements': {'شبح (Ghost)': 1},
        'min_level': 1,
        'description': 'نیاز: 1 شبح (Ghost)'
    },
    'حمله برق‌آسا': {
        'multiplier': 1.5,
        'requirements': {'رعد (Thunder)': 1},
        'min_level': 2,
        'description': 'نیاز: 1 رعد (Thunder)'
    },
    'حمله صاعقه': {
        'multiplier': 2.0,
        'requirements': {'تندر (Boomer)': 1},
        'min_level': 3,
        'description': 'نیاز: 1 تندر (Boomer)'
    },
    'حمله آخرالزمانی': {
        'multiplier': 5.0,
        'requirements': {'آپوکالیپس (Apocalypse)': 1, 'zone_gem': 10},
        'min_level': 10,
        'description': 'نیاز: 1 آپوکالیپس + 10 جم'
    }
}

@dp.message(F.text == "🏪 بازار")
async def cmd_market(message: Message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await message.answer("❌ ابتدا با /start ثبت نام کنید!")
        return
    
    # دریافت موشک‌های کاربر
    user_missiles = db.get_user_missiles(user_id)
    user_missiles_dict = {m['missile_name']: m['quantity'] for m in user_missiles}
    
    # ایجاد کیبورد برای بازار
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="شبح (Ghost)", callback_data="buy_ghost"),
            InlineKeyboardButton(text="رعد (Thunder)", callback_data="buy_thunder")
        ],
        [
            InlineKeyboardButton(text="تندر (Boomer)", callback_data="buy_boomer"),
            InlineKeyboardButton(text="هاوک (Hawk)", callback_data="buy_hawk")
        ],
        [
            InlineKeyboardButton(text="پاتریوت (Patriot)", callback_data="buy_patriot"),
            InlineKeyboardButton(text="⏩ موشک‌های ویژه", callback_data="market_special")
        ],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")]
    ])
    
    # نمایش موجودی موشک‌ها
    missiles_text = ""
    common_missiles = ['شبح (Ghost)', 'رعد (Thunder)', 'تندر (Boomer)']
    for missile_name in common_missiles:
        qty = user_missiles_dict.get(missile_name, 0)
        missiles_text += f"• {missile_name}: {qty} عدد\n"
    
    market_text = f"""
🏪 <b>بازار جنگ‌افزار</b>
━━━━━━━━━━━━━━
💰 سکه شما: {user['zone_coin']} ZC
💎 جم شما: {user['zone_gem']} ZG
🎯 لول: {user['level']}
━━━━━━━━━━━━━━
📊 <b>موشک‌های شما:</b>
{missiles_text if missiles_text else "• هیچ موشکی ندارید!"}
━━━━━━━━━━━━━━
📦 <b>موشک‌های معمولی:</b>

1. شبح (Ghost)
   • قدرت: 50 آسیب
   • قیمت: 200 ZC
   • نیاز لول: 1

2. رعد (Thunder)
   • قدرت: 70 آسیب  
   • قیمت: 500 ZC
   • نیاز لول: 2

3. تندر (Boomer)
   • قدرت: 90 آسیب
   • قیمت: 1000 ZC
   • نیاز لول: 3

4. هاوک (Hawk)
   • قدرت: 110 آسیب
   • قیمت: 2000 ZC
   • نیاز لول: 4

5. پاتریوت (Patriot)
   • قدرت: 130 آسیب
   • قیمت: 5000 ZC
   • نیاز لول: 5
    """
    
    await message.answer(market_text, reply_markup=keyboard)

@dp.callback_query(F.data == "market_special")
async def cmd_market_special(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="شهاب (Meteor)", callback_data="buy_meteor"),
            InlineKeyboardButton(text="سیل (Tsunami)", callback_data="buy_tsunami")
        ],
        [
            InlineKeyboardButton(text="توفان (Storm)", callback_data="buy_storm"),
            InlineKeyboardButton(text="تایفون (Typhoon)", callback_data="buy_typhoon")
        ],
        [
            InlineKeyboardButton(text="آپوکالیپس (Apocalypse)", callback_data="buy_apocalypse"),
            InlineKeyboardButton(text="⏪ موشک‌های معمولی", callback_data="market_normal")
        ]
    ])
    
    special_text = f"""
💎 <b>موشک‌های ویژه</b>
━━━━━━━━━━━━━━
💰 سکه شما: {user['zone_coin']} ZC
💎 جم شما: {user['zone_gem']} ZG
🎯 لول: {user['level']}
━━━━━━━━━━━━━━
💣 <b>موشک‌های ویژه:</b>

1. شهاب (Meteor)
   • قدرت: 250 آسیب
   • قیمت: 25,000 ZC + 1 جم
   • نیاز لول: 6

2. سیل (Tsunami)
   • قدرت: 300 آسیب
   • قیمت: 30,000 ZC + 2 جم
   • نیاز لول: 7

3. توفان (Storm)
   • قدرت: 350 آسیب  
   • قیمت: 35,000 ZC + 3 جم
   • نیاز لول: 8

4. تایفون (Typhoon)
   • قدرت: 400 آسیب
   • قیمت: 40,000 ZC + 4 جم
   • نیاز لول: 9

5. آپوکالیپس (Apocalypse)
   • قدرت: 500 آسیب
   • قیمت: 50,000 ZC + 5 جم
   • نیاز لول: 10
    """
    
    await callback.message.edit_text(special_text, reply_markup=keyboard)

@dp.callback_query(F.data == "market_normal")
async def cmd_market_normal(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="شبح (Ghost)", callback_data="buy_ghost"),
            InlineKeyboardButton(text="رعد (Thunder)", callback_data="buy_thunder")
        ],
        [
            InlineKeyboardButton(text="تندر (Boomer)", callback_data="buy_boomer"),
            InlineKeyboardButton(text="هاوک (Hawk)", callback_data="buy_hawk")
        ],
        [
            InlineKeyboardButton(text="پاتریوت (Patriot)", callback_data="buy_patriot"),
            InlineKeyboardButton(text="⏩ موشک‌های ویژه", callback_data="market_special")
        ]
    ])
    
    market_text = f"""
🏪 <b>بازار جنگ‌افزار</b>
━━━━━━━━━━━━━━
💰 سکه شما: {user['zone_coin']} ZC
💎 جم شما: {user['zone_gem']} ZG
🎯 لول: {user['level']}
━━━━━━━━━━━━━━
📦 <b>موشک‌های معمولی:</b>

1. شبح (Ghost) - 200 ZC
2. رعد (Thunder) - 500 ZC  
3. تندر (Boomer) - 1000 ZC
4. هاوک (Hawk) - 2000 ZC
5. پاتریوت (Patriot) - 5000 ZC
    """
    
    await callback.message.edit_text(market_text, reply_markup=keyboard)

@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: CallbackQuery):
    missile_type = callback.data.replace("buy_", "")
    
    missile_map = {
        # موشک‌های معمولی
        'ghost': 'شبح (Ghost)',
        'thunder': 'رعد (Thunder)',
        'boomer': 'تندر (Boomer)',
        'hawk': 'هاوک (Hawk)',
        'patriot': 'پاتریوت (Patriot)',
        
        # موشک‌های ویژه
        'meteor': 'شهاب (Meteor)',
        'tsunami': 'سیل (Tsunami)',
        'storm': 'توفان (Storm)',
        'typhoon': 'تایفون (Typhoon)',
        'apocalypse': 'آپوکالیپس (Apocalypse)'
    }
    
    if missile_type not in missile_map:
        await callback.answer("❌ این آیتم موجود نیست!")
        return
    
    missile_name = missile_map[missile_type]
    missile_data = MISSILE_DATA.get(missile_name)
    
    if not missile_data:
        await callback.answer("❌ خطا در دریافت اطلاعات!")
        return
    
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    
    # بررسی سطح
    if user['level'] < missile_data['min_level']:
        await callback.answer(f"❌ نیاز به لول {missile_data['min_level']} دارید! (لول شما: {user['level']})")
        return
    
    # بررسی موجودی سکه
    if user['zone_coin'] < missile_data['price']:
        await callback.answer(f"❌ سکه کافی ندارید! نیاز: {missile_data['price']} ZC")
        return
    
    # بررسی موجودی جم برای موشک‌های ویژه
    if missile_data['type'] == 'special' and missile_data.get('gem_cost', 0) > 0:
        if user['zone_gem'] < missile_data['gem_cost']:
            await callback.answer(f"❌ جم کافی ندارید! نیاز: {missile_data['gem_cost']} جم")
            return
    
    # خرید
    db.update_user_coins(user_id, -missile_data['price'])
    
    if missile_data['type'] == 'special' and missile_data.get('gem_cost', 0) > 0:
        db.update_user_gems(user_id, -missile_data['gem_cost'])
    
    # افزودن موشک
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO user_missiles (user_id, missile_name, quantity)
    VALUES (?, ?, 1)
    ON CONFLICT(user_id, missile_name) 
    DO UPDATE SET quantity = quantity + 1
    ''', (user_id, missile_name))
    conn.commit()
    conn.close()
    
    # گزارش خرید
    gem_text = f" + {missile_data['gem_cost']} جم" if missile_data.get('gem_cost', 0) > 0 else ""
    
    report_text = f"""
✅ <b>خرید موفق!</b>
━━━━━━━━━━━━━━
📦 آیتم: {missile_name}
💰 قیمت: {missile_data['price']} ZC{gem_text}
💥 قدرت: {missile_data['damage']} آسیب
🎯 نیاز لول: {missile_data['min_level']}
━━━━━━━━━━━━━━
💰 سکه باقی‌مانده: {user['zone_coin'] - missile_data['price']} ZC
💎 جم باقی‌مانده: {user['zone_gem'] - missile_data.get('gem_cost', 0)} ZG
    """
    
    await callback.message.edit_text(report_text)
    await callback.answer("✅ خرید با موفقیت انجام شد!")
    @dp.message(F.text == "🎁 باکس")
async def cmd_boxes(message: Message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await message.answer("❌ ابتدا با /start ثبت نام کنید!")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎁 باکس سکه (500 ZC)", callback_data="box_coin"),
            InlineKeyboardButton(text="🎁 باکس ZP (1000 ZC)", callback_data="box_zp")
        ],
        [
            InlineKeyboardButton(text="💎 باکس ویژه (5 ZG)", callback_data="box_special"),
            InlineKeyboardButton(text="👑 باکس افسانه‌ای (10 ZG)", callback_data="box_legendary")
        ],
        [
            InlineKeyboardButton(text="🆓 باکس رایگان", callback_data="box_free"),
            InlineKeyboardButton(text="📦 موجودی باکس‌ها", callback_data="box_inventory")
        ],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")]
    ])
    
    box_text = f"""
🎁 <b>فروشگاه باکس‌ها</b>
━━━━━━━━━━━━━━
💰 سکه شما: {user['zone_coin']} ZC
💎 جم شما: {user['zone_gem']} ZG
⚡ ZP شما: {user['zone_point']} ZP
━━━━━━━━━━━━━━
🎰 شانس خود را امتحان کنید و جایزه بگیرید!

1. 🎁 <b>باکس سکه</b>
   • قیمت: 500 سکه
   • جایزه: 100-2000 سکه
   
2. 🎁 <b>باکس ZP</b>
   • قیمت: 1000 سکه
   • جایزه: 50-500 ZP

3. 💎 <b>باکس ویژه</b>
   • قیمت: 5 جم
   • جایزه: موشک‌های ویژه

4. 👑 <b>باکس افسانه‌ای</b>
   • قیمت: 10 جم
   • جایزه: ترکیبی (شانس 10% جکپات)

5. 🆓 <b>باکس رایگان</b>
   • قیمت: رایگان
   • جایزه: 10-100 (تصادفی)
   • بازدید بعدی: 24 ساعت بعد
    """
    
    await message.answer(box_text, reply_markup=keyboard)

@dp.callback_query(F.data.startswith("box_"))
async def process_box(callback: CallbackQuery):
    box_type = callback.data.replace("box_", "")
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await callback.answer("❌ کاربر یافت نشد!")
        return
    
    rewards = {
        'coin': {'min': 100, 'max': 2000, 'cost_coin': 500, 'cost_gem': 0},
        'zp': {'min': 50, 'max': 500, 'cost_coin': 1000, 'cost_gem': 0},
        'special': {'min': 1, 'max': 3, 'cost_coin': 0, 'cost_gem': 5, 'type': 'missile'},
        'legendary': {'min': 1000, 'max': 10000, 'cost_coin': 0, 'cost_gem': 10, 'type': 'mixed'},
        'free': {'min': 10, 'max': 100, 'cost_coin': 0, 'cost_gem': 0, 'cooldown': 86400}  # 24 ساعت
    }
    
    if box_type not in rewards:
        await callback.answer("❌ باکس نامعتبر!")
        return
    
    reward = rewards[box_type]
    
    # بررسی موجودی برای باکس‌های پولی
    if box_type != 'free':
        if user['zone_coin'] < reward['cost_coin']:
            await callback.answer("❌ سکه کافی ندارید!")
            return
        
        if user['zone_gem'] < reward['cost_gem']:
            await callback.answer("❌ جم کافی ندارید!")
            return
    
    # کسر هزینه برای باکس‌های پولی
    if reward['cost_coin'] > 0:
        db.update_user_coins(user_id, -reward['cost_coin'])
    if reward['cost_gem'] > 0:
        db.update_user_gems(user_id, -reward['cost_gem'])
    
    # تولید جایزه
    prize_text = ""
    prize_value = 0
    
    if box_type == 'free':
        prize = random.randint(reward['min'], reward['max'])
        prize_type = random.choice(['coin', 'zp'])
        
        if prize_type == 'coin':
            db.update_user_coins(user_id, prize)
            prize_text = f"{prize} سکه"
            prize_value = prize
        else:
            db.update_user_zp(user_id, prize)
            prize_text = f"{prize} ZP"
            prize_value = prize
    
    elif box_type == 'special':
        # جایزه موشک ویژه
        special_missiles = ['شهاب (Meteor)', 'سیل (Tsunami)', 'توفان (Storm)']
        missile = random.choice(special_missiles)
        
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO user_missiles (user_id, missile_name, quantity)
        VALUES (?, ?, 1)
        ON CONFLICT(user_id, missile_name) 
        DO UPDATE SET quantity = quantity + 1
        ''', (user_id, missile))
        conn.commit()
        conn.close()
        
        prize_text = f"1 عدد {missile}"
        prize_value = MISSILE_DATA[missile]['price']
    
    elif box_type == 'legendary':
        # شانس 10% برای جایزه ویژه
        if random.random() < 0.1:  # 10% شانس جکپات
            prize = random.randint(5000, 20000)
            db.update_user_coins(user_id, prize)
            prize_text = f"🎉 جکپات! {prize} سکه"
            prize_value = prize
        else:
            prize = random.randint(reward['min'], reward['max'])
            db.update_user_coins(user_id, prize)
            prize_text = f"{prize} سکه"
            prize_value = prize
    
    else:  # باکس‌های معمولی
        prize = random.randint(reward['min'], reward['max'])
        if box_type == 'coin':
            db.update_user_coins(user_id, prize)
            prize_text = f"{prize} سکه"
            prize_value = prize
        else:  # zp
            db.update_user_zp(user_id, prize)
            prize_text = f"{prize} ZP"
            prize_value = prize
    
    # نام باکس
    box_names = {
        'coin': 'باکس سکه',
        'zp': 'باکس ZP',
        'special': 'باکس ویژه',
        'legendary': 'باکس افسانه‌ای',
        'free': 'باکس رایگان'
    }
    
    # گزارش
    report_text = f"""
🎉 <b>باکس باز شد!</b>
━━━━━━━━━━━━━━
🎁 نوع باکس: {box_names[box_type]}
🎰 جایزه: {prize_text}
💰 ارزش تقریبی: {prize_value} ZC
━━━━━━━━━━━━━━
💰 سکه فعلی: {user['zone_coin'] - reward['cost_coin'] + (prize if box_type == 'coin' or box_type == 'legendary' else 0)}
💎 جم فعلی: {user['zone_gem'] - reward['cost_gem']}
⚡ ZP فعلی: {user['zone_point'] + (prize if box_type == 'zp' else 0)}
━━━━━━━━━━━━━━
{'🎊 تبریک! شانس با شما یار بود!' if box_type == 'legendary' and random.random() < 0.1 else ''}
    """
    
    await callback.message.edit_text(report_text)
    await callback.answer("✅ باکس با موفقیت باز شد!")
    
