#!/usr/bin/env python3
"""
Warzone Telegram Bot - Version 1.0.0
کاملترین ربات جنگی تلگرام با قابلیت‌های پیشرفته
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
    waiting_for_target = State()
    waiting_for_attack_type = State()
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
        'min_level': 1
    },
    'حمله متوسط': {
        'multiplier': 1.5,
        'requirements': {'موشک میان برد': 1},
        'min_level': 2
    },
    'حمله پیشرفته': {
        'multiplier': 2.0,
        'requirements': {'موشک بالستیک': 1},
        'min_level': 3
    },
    'حمله ویرانگر': {
        'multiplier': 5.0,
        'requirements': {'موشک هسته‌ای': 1, 'zone_gem': 10},
        'min_level': 10
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
        resize_keyboard=True
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
        resize_keyboard=True
    )
    return keyboard

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
    
    # تنظیم ادمین اگر در لیست باشد
    if user_id in ADMIN_IDS:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET is_admin = 1 WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
    
    welcome_text = """
🚀 <b>به جنگ‌افزار خوش آمدید!</b>

🎮 <i>یک ربات جنگی کامل با قابلیت‌های:</i>
• ⚔️ سیستم حمله پیشرفته
• 🏪 بازار خرید موشک
• 🎁 باکس‌های مختلف
• ⛏️ سیستم ماینینگ
• 🏰 سیستم دفاع
• 📊 رنکینگ رقابتی

📖 برای شروع از دکمه‌های زیر استفاده کنید:
    """
    
    await message.answer(welcome_text, reply_markup=create_main_keyboard())

@dp.message(F.text == "👤 پروفایل")
async def cmd_profile(message: Message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await message.answer("❌ کاربر یافت نشد!")
        return
    
    # محاسبه ZP قابل دریافت از ماینر
    miner_zp = 0
    if user['last_miner_claim']:
        time_passed = int(time.time()) - user['last_miner_claim']
        zp_per_hour = MINER_LEVELS[user['miner_level']]['zp_per_hour']
        miner_zp = int((time_passed / 3600) * zp_per_hour)
    
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
🏰 سیستم دفاع:
• 🚀 دفاع موشکی: لول {user['defense_missile_level']}
• 📡 جنگ الکترونیک: لول {user['defense_electronic_level']}
• ✈️ ضد جنگنده: لول {user['defense_antifighter_level']}
• 🛡️ بانس کلی: {user['total_defense_bonus']*100:.1f}%
━━━━━━━━━━━━━━
📅 عضویت: {datetime.fromtimestamp(user['created_at']).strftime('%Y/%m/%d')}
    """
    
    await message.answer(profile_text)

@dp.message(F.text == "⚔️ حمله")
async def cmd_attack(message: Message):
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
    
    await message.answer("⚔️ <b>انتخاب نوع حمله:</b>", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("attack_"))
async def process_attack_type(callback: CallbackQuery, state: FSMContext):
    attack_type = callback.data.replace("attack_", "")
    
    # ذخیره نوع حمله
    await state.update_data(attack_type=attack_type)
    await state.set_state(UserStates.waiting_for_target)
    
    await callback.message.edit_text("🆔 لطفا آیدی عددی کاربر مورد نظر را ارسال کنید:")

@dp.message(UserStates.waiting_for_target)
async def process_target_id(message: Message, state: FSMContext):
    try:
        target_id = int(message.text)
        
        # بررسی وجود کاربر
        target_user = db.get_user(target_id)
        if not target_user:
            await message.answer("❌ کاربر مورد نظر یافت نشد!")
            await state.clear()
            return
        
        # بررسی حمله به خود
        if target_id == message.from_user.id:
            await message.answer("❌ نمی‌توانید به خود حمله کنید!")
            await state.clear()
            return
        
        data = await state.get_data()
        attack_type = data['attack_type']
        
        # انجام حمله
        await execute_attack(message.from_user.id, target_id, attack_type, message)
        
        await state.clear()
        
    except ValueError:
        await message.answer("❌ آیدی باید عدد باشد!")
    except Exception as e:
        logger.error(f"Attack error: {e}")
        await message.answer("❌ خطا در انجام حمله!")
        await state.clear()

async def execute_attack(attacker_id: int, target_id: int, attack_type: str, message: Message):
    attacker = db.get_user(attacker_id)
    target = db.get_user(target_id)
    
    if not attacker or not target:
        await message.answer("❌ کاربر یافت نشد!")
        return
    
    # بررسی سطح
    combo = None
    if attack_type == 'simple':
        combo = ATTACK_COMBOS['حمله ساده']
    elif attack_type == 'medium':
        combo = ATTACK_COMBOS['حمله متوسط']
    elif attack_type == 'advanced':
        combo = ATTACK_COMBOS['حمله پیشرفته']
    elif attack_type == 'nuclear':
        combo = ATTACK_COMBOS['حمله ویرانگر']
    
    if attacker['level'] < combo['min_level']:
        await message.answer(f"❌ برای این حمله حداقل لول {combo['min_level']} نیاز دارید!")
        return
    
    # بررسی نیازمندی‌ها
    for req, amount in combo['requirements'].items():
        if req in MISSILE_DATA:
            # بررسی موشک
            missiles = db.get_user_missiles(attacker_id)
            missile_qty = next((m['quantity'] for m in missiles if m['missile_name'] == req), 0)
            if missile_qty < amount:
                await message.answer(f"❌ {req} کافی ندارید! (نیاز: {amount})")
                return
        elif req == 'zone_gem':
            if attacker['zone_gem'] < amount:
                await message.answer(f"❌ جم کافی ندارید! (نیاز: {amount})")
                return
    
    # محاسبه خسارت با در نظر گرفتن دفاع
    base_damage = 100  # damage base
    actual_damage = int(base_damage * combo['multiplier'] * (1 - target['total_defense_bonus']))
    
    # محاسبه غنیمت
    loot_coins = min(int(target['zone_coin'] * 0.1), 1000)
    loot_gems = min(int(target['zone_gem'] * 0.05), 10)
    
    # کسر منابع از هدف
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
    
    # ثبت حمله
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO attacks (attacker_id, target_id, attack_type, damage, loot_coins, loot_gems)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (attacker_id, target_id, attack_type, actual_damage, loot_coins, loot_gems))
    conn.commit()
    conn.close()
    
    # اضافه کردن XP
    level_up, new_level = db.add_xp(attacker_id, 50)
    
        # ارسال گزارش
    report_text = f"""
🎯 <b>حمله موفق!</b>
━━━━━━━━━━━━━━
⚔️ حمله‌کننده: {attacker['full_name']}
🎯 هدف: {target['full_name']}
💥 نوع حمله: {list(ATTACK_COMBOS.keys())[['simple','medium','advanced','nuclear'].index(attack_type)]}
🛡️ کاهش بانس دفاع: {target['total_defense_bonus']*100:.1f}%
💢 خسارت وارد شده: {actual_damage}
━━━━━━━━━━━━━━
💰 غنیمت سکه: {loot_coins} ZC
💎 غنیمت جم: {loot_gems} ZG
━━━━━━━━━━━━━━
⭐ XP کسب شده: 50
{'🎉 سطح شما افزایش یافت!' if level_up else ''}
    """
    
    await message.answer(report_text)
    
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
        """
        await bot.send_message(target_id, target_report)
    except:
        pass

@dp.message(F.text == "🏪 بازار")
async def cmd_market(message: Message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await message.answer("❌ ابتدا با /start ثبت نام کنید!")
        return
    
    # ایجاد کیبورد برای بازار
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="موشک کوتاه برد (200 ZC)", callback_data="buy_short"),
            InlineKeyboardButton(text="موشک میان برد (500 ZC)", callback_data="buy_medium")
        ],
        [
            InlineKeyboardButton(text="موشک بالستیک (1000 ZC)", callback_data="buy_ballistic"),
            InlineKeyboardButton(text="موشک هدایت شونده (2000 ZC)", callback_data="buy_guided")
        ],
        [
            InlineKeyboardButton(text="موشک زمین به هوا (5000 ZC)", callback_data="buy_sam"),
            InlineKeyboardButton(text="⏪ صفحه قبل", callback_data="market_page2")
        ]
    ])
    
    market_text = """
🏪 <b>بازار جنگ‌افزار</b>
━━━━━━━━━━━━━━
💰 سکه شما: {coins} ZC
💎 جم شما: {gems} ZG
━━━━━━━━━━━━━━
📦 <i>موشک‌های معمولی:</i>
    """.format(coins=user['zone_coin'], gems=user['zone_gem'])
    
    await message.answer(market_text, reply_markup=keyboard)

@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: CallbackQuery):
    missile_type = callback.data.replace("buy_", "")
    
    missile_map = {
        'short': 'موشک کوتاه برد',
        'medium': 'موشک میان برد',
        'ballistic': 'موشک بالستیک',
        'guided': 'موشک هدایت شونده',
        'sam': 'موشک زمین به هوا'
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
        await callback.answer(f"❌ نیاز به لول {missile_data['min_level']} دارید!")
        return
    
    # بررسی موجودی سکه
    if user['zone_coin'] < missile_data['price']:
        await callback.answer("❌ سکه کافی ندارید!")
        return
    
    # خرید
    db.update_user_coins(user_id, -missile_data['price'])
    
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
    report_text = f"""
✅ <b>خرید موفق!</b>
━━━━━━━━━━━━━━
📦 آیتم: {missile_name}
💰 قیمت: {missile_data['price']} ZC
💎 جم مصرفی: {missile_data.get('gem_cost', 0)} ZG
💥 قدرت: {missile_data['damage']}
━━━━━━━━━━━━━━
💰 سکه باقی‌مانده: {user['zone_coin'] - missile_data['price']} ZC
    """
    
    await callback.message.edit_text(report_text)
    await callback.answer("✅ خرید با موفقیت انجام شد!")

@dp.message(F.text == "🎁 باکس")
async def cmd_boxes(message: Message):
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
            InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")
        ]
    ])
    
    box_text = """
🎁 <b>فروشگاه باکس‌ها</b>
━━━━━━━━━━━━━━
🎰 شانس خود را امتحان کنید و جایزه بگیرید!

1. 🎁 باکس سکه
   • قیمت: 500 سکه
   • جایزه: 100-2000 سکه

2. 🎁 باکس ZP
   • قیمت: 1000 سکه
   • جایزه: 50-500 ZP

3. 💎 باکس ویژه
   • قیمت: 5 جم
   • جایزه: موشک‌های قوی

4. 👑 باکس افسانه‌ای
   • قیمت: 10 جم
   • جایزه: ترکیبی (شانس 10%)

5. 🆓 باکس رایگان
   • قیمت: رایگان
   • جایزه: 10-100 (تصادفی)
    """
    
    await message.answer(box_text, reply_markup=keyboard)

@dp.callback_query(F.data.startswith("box_"))
async def process_box(callback: CallbackQuery):
    box_type = callback.data.replace("box_", "")
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    
    rewards = {
        'coin': {'min': 100, 'max': 2000, 'cost_coin': 500, 'cost_gem': 0},
        'zp': {'min': 50, 'max': 500, 'cost_coin': 1000, 'cost_gem': 0},
        'special': {'min': 1, 'max': 3, 'cost_coin': 0, 'cost_gem': 5, 'type': 'missile'},
        'legendary': {'min': 1000, 'max': 10000, 'cost_coin': 0, 'cost_gem': 10, 'type': 'mixed'},
        'free': {'min': 10, 'max': 100, 'cost_coin': 0, 'cost_gem': 0}
    }
    
    if box_type not in rewards:
        await callback.answer("❌ باکس نامعتبر!")
        return
    
    reward = rewards[box_type]
    
    # بررسی موجودی
    if user['zone_coin'] < reward['cost_coin']:
        await callback.answer("❌ سکه کافی ندارید!")
        return
    
    if user['zone_gem'] < reward['cost_gem']:
        await callback.answer("❌ جم کافی ندارید!")
        return
    
    # کسر هزینه
    if reward['cost_coin'] > 0:
        db.update_user_coins(user_id, -reward['cost_coin'])
    if reward['cost_gem'] > 0:
        db.update_user_gems(user_id, -reward['cost_gem'])
    
    # تولید جایزه
    if box_type == 'free':
        prize = random.randint(reward['min'], reward['max'])
        prize_type = random.choice(['coin', 'zp'])
        
        if prize_type == 'coin':
            db.update_user_coins(user_id, prize)
            prize_text = f"{prize} سکه"
        else:
            db.update_user_zp(user_id, prize)
            prize_text = f"{prize} ZP"
    
    elif box_type == 'special':
        # جایزه موشک
        missiles = ['موشک زلزله', 'موشک سونامی', 'موشک خورشیدی']
        missile = random.choice(missiles)
        
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
    
    elif box_type == 'legendary':
        # شانس 10% برای جایزه ویژه
        if random.random() < 0.1:
            prize = random.randint(5000, 20000)
            db.update_user_coins(user_id, prize)
            prize_text = f"🎉 جکپات! {prize} سکه"
        else:
            prize = random.randint(reward['min'], reward['max'])
            db.update_user_coins(user_id, prize)
            prize_text = f"{prize} سکه"
    
    else:
        # باکس‌های معمولی
        prize = random.randint(reward['min'], reward['max'])
        if box_type == 'coin':
            db.update_user_coins(user_id, prize)
            prize_text = f"{prize} سکه"
        else:  # zp
            db.update_user_zp(user_id, prize)
            prize_text = f"{prize} ZP"
    
    # گزارش
    report_text = f"""
🎉 <b>باکس باز شد!</b>
━━━━━━━━━━━━━━
🎁 نوع باکس: {box_type}
🎰 جایزه: {prize_text}
━━━━━━━━━━━━━━
💰 سکه فعلی: {user['zone_coin'] - reward['cost_coin'] + (prize if box_type == 'coin' else 0)}
💎 جم فعلی: {user['zone_gem'] - reward['cost_gem']}
⚡ ZP فعلی: {user['zone_point'] + (prize if box_type == 'zp' else 0)}
    """
    
    await callback.message.edit_text(report_text)
    await callback.answer("✅ باکس با موفقیت باز شد!")

@dp.message(F.text == "⛏️ ماینر")
async def cmd_miner(message: Message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await message.answer("❌ ابتدا با /start ثبت نام کنید!")
        return
    
    # محاسبه ZP قابل دریافت
    miner_zp = 0
    if user['last_miner_claim']:
        time_passed = int(time.time()) - user['last_miner_claim']
        zp_per_hour = MINER_LEVELS[user['miner_level']]['zp_per_hour']
        miner_zp = int((time_passed / 3600) * zp_per_hour)
    
    # ایجاد کیبورد ماینر
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📦 دریافت {miner_zp} ZP", callback_data="claim_miner")],
        [InlineKeyboardButton(text=f"⬆️ ارتقا ماینر (هزینه: {MINER_LEVELS[user['miner_level']]['upgrade_cost']} ZC)", callback_data="upgrade_miner")],
        [InlineKeyboardButton(text="📊 اطلاعات ماینر", callback_data="miner_info")]
    ])
    
    miner_text = f"""
⛏️ <b>سیستم ماینینگ</b>
━━━━━━━━━━━━━━
📊 سطح ماینر: {user['miner_level']}
⚡ تولید در ساعت: {MINER_LEVELS[user['miner_level']]['zp_per_hour']} ZP
💰 هزینه ارتقا: {MINER_LEVELS[user['miner_level']]['upgrade_cost']} ZC
━━━━━━━━━━━━━━
📦 ZP قابل دریافت: {miner_zp}
⏰ آخرین دریافت: {datetime.fromtimestamp(user['last_miner_claim']).strftime('%H:%M') if user['last_miner_claim'] else 'هرگز'}
━━━━━━━━━━━━━━
📈 سطح بعدی: {user['miner_level'] + 1 if user['miner_level'] < 15 else 'ماکس'}
⚡ تولید بعدی: {MINER_LEVELS.get(user['miner_level'] + 1, {}).get('zp_per_hour', 'ماکس')} ZP/ساعت
    """
    
    await message.answer(miner_text, reply_markup=keyboard)

@dp.callback_query(F.data == "claim_miner")
async def process_claim_miner(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await callback.answer("❌ کاربر یافت نشد!")
        return
    
    # محاسبه ZP قابل دریافت
    miner_zp = 0
    if user['last_miner_claim']:
        time_passed = int(time.time()) - user['last_miner_claim']
        zp_per_hour = MINER_LEVELS[user['miner_level']]['zp_per_hour']
        miner_zp = int((time_passed / 3600) * zp_per_hour)
    
    if miner_zp <= 0:
        await callback.answer("❌ هنوز ZP جدیدی تولید نشده!")
        return
    
    # دریافت ZP
    db.update_user_zp(user_id, miner_zp)
    
    # آپدیت زمان آخرین دریافت
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET last_miner_claim = ? WHERE user_id = ?', 
                  (int(time.time()), user_id))
    conn.commit()
    conn.close()
    
    await callback.message.edit_text(f"""
✅ <b>دریافت موفق!</b>
━━━━━━━━━━━━━━
⛏️ ZP دریافتی: {miner_zp}
💰 ZP کل: {user['zone_point'] + miner_zp}
⏰ زمان دریافت: {datetime.now().strftime('%H:%M')}
━━━━━━━━━━━━━━
⚡ ماینر همچنان در حال تولید است...
    """)
    await callback.answer(f"✅ {miner_zp} ZP دریافت شد!")

@dp.callback_query(F.data == "upgrade_miner")
async def process_upgrade_miner(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await callback.answer("❌ کاربر یافت نشد!")
        return
    
    current_level = user['miner_level']
    
    # بررسی ماکس لول
    if current_level >= 15:
        await callback.answer("🎉 ماینر شما در ماکس لول است!")
        return
    
    upgrade_cost = MINER_LEVELS[current_level]['upgrade_cost']
    
    # بررسی موجودی
    if user['zone_coin'] < upgrade_cost:
        await callback.answer(f"❌ سکه کافی ندارید! نیاز: {upgrade_cost} ZC")
        return
    
    # ارتقا
    db.update_user_coins(user_id, -upgrade_cost)
    
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET miner_level = miner_level + 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    
    new_level = current_level + 1
    
    await callback.message.edit_text(f"""
⬆️ <b>ارتقا موفق!</b>
━━━━━━━━━━━━━━
⛏️ سطح جدید: {new_level}
⚡ تولید جدید: {MINER_LEVELS[new_level]['zp_per_hour']} ZP/ساعت
💰 هزینه پرداختی: {upgrade_cost} ZC
━━━━━━━━━━━━━━
💰 سکه باقی‌مانده: {user['zone_coin'] - upgrade_cost}
🎉 ماینر شما با قدرت بیشتر کار می‌کند!
    """)
    await callback.answer(f"✅ ماینر به سطح {new_level} ارتقا یافت!")

@dp.message(F.text == "🏰 دفاع")
async def cmd_defense(message: Message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await message.answer("❌ ابتدا با /start ثبت نام کنید!")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"🚀 دفاع موشکی (لول {user['defense_missile_level']})", callback_data="upgrade_missile_def"),
            InlineKeyboardButton(text=f"📡 جنگ الکترونیک (لول {user['defense_electronic_level']})", callback_data="upgrade_electronic_def")
        ],
        [
            InlineKeyboardButton(text=f"✈️ ضد جنگنده (لول {user['defense_antifighter_level']})", callback_data="upgrade_antifighter_def"),
            InlineKeyboardButton(text="📊 اطلاعات دفاع", callback_data="defense_info")
        ]
    ])
    
    defense_text = f"""
🏰 <b>سیستم دفاع</b>
━━━━━━━━━━━━━━
🛡️ بانس دفاع کلی: {user['total_defense_bonus']*100:.1f}%
━━━━━━━━━━━━━━
🚀 دفاع موشکی:
   • لول: {user['defense_missile_level']}
   • بانس: {user['defense_missile_level'] * 5}%
   • هزینه ارتقا: {user['defense_missile_level'] * 1000} ZC

📡 جنگ الکترونیک:
   • لول: {user['defense_electronic_level']}
   • بانس: {user['defense_electronic_level'] * 3}%
   • هزینه ارتقا: {user['defense_electronic_level'] * 800} ZC

✈️ ضد جنگنده:
   • لول: {user['defense_antifighter_level']}
   • بانس: {user['defense_antifighter_level'] * 7}%
   • هزینه ارتقا: {user['defense_antifighter_level'] * 1200} ZC
━━━━━━━━━━━━━━
💰 سکه شما: {user['zone_coin']} ZC
    """
    
    await message.answer(defense_text, reply_markup=keyboard)

@dp.callback_query(F.data.startswith("upgrade_"))
async def process_upgrade_defense(callback: CallbackQuery):
    defense_type = callback.data.replace("upgrade_", "").replace("_def", "")
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await callback.answer("❌ کاربر یافت نشد!")
        return
    
    # محاسبه هزینه ارتقا
    current_level = 0
    cost_multiplier = 0
    
    if defense_type == 'missile':
        current_level = user['defense_missile_level']
        cost_multiplier = 1000
    elif defense_type == 'electronic':
        current_level = user['defense_electronic_level']
        cost_multiplier = 800
    elif defense_type == 'antifighter':
        current_level = user['defense_antifighter_level']
        cost_multiplier = 1200
    
    upgrade_cost = (current_level + 1) * cost_multiplier
    
    # بررسی موجودی
    if user['zone_coin'] < upgrade_cost:
        await callback.answer(f"❌ سکه کافی ندارید! نیاز: {upgrade_cost} ZC")
        return
    
    # ارتقا
    db.update_user_coins(user_id, -upgrade_cost)
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    if defense_type == 'missile':
        cursor.execute('UPDATE users SET defense_missile_level = defense_missile_level + 1 WHERE user_id = ?', (user_id,))
    elif defense_type == 'electronic':
        cursor.execute('UPDATE users SET defense_electronic_level = defense_electronic_level + 1 WHERE user_id = ?', (user_id,))
    elif defense_type == 'antifighter':
        cursor.execute('UPDATE users SET defense_antifighter_level = defense_antifighter_level + 1 WHERE user_id = ?', (user_id,))
    
    # محاسبه بانس جدید
    cursor.execute('''
    UPDATE users SET total_defense_bonus = 
        (defense_missile_level * 0.05) + 
        (defense_electronic_level * 0.03) + 
        (defense_antifighter_level * 0.07)
    WHERE user_id = ?
    ''', (user_id,))
    
    conn.commit()
    conn.close()
    
    # نام دفاع
    defense_names = {
        'missile': 'دفاع موشکی',
        'electronic': 'جنگ الکترونیک',
        'antifighter': 'ضد جنگنده'
    }
    
    await callback.message.edit_text(f"""
🛡️ <b>ارتقا موفق!</b>
━━━━━━━━━━━━━━
🏰 سیستم: {defense_names[defense_type]}
📈 لول جدید: {current_level + 1}
💰 هزینه: {upgrade_cost} ZC
━━━━━━━━━━━━━━
🛡️ بانس دفاع کلی: {min((current_level + 1) * (5 if defense_type == 'missile' else 3 if defense_type == 'electronic' else 7), 50)}%
💰 سکه باقی‌مانده: {user['zone_coin'] - upgrade_cost}
    """)
    await callback.answer(f"✅ {defense_names[defense_type]} ارتقا یافت!")

@dp.message(F.text == "📊 رنکینگ")
async def cmd_ranking(message: Message):
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # رنکینگ بر اساس سکه
    cursor.execute('''
    SELECT user_id, username, full_name, zone_coin, zone_gem, zone_point, level
    FROM users 
    ORDER BY zone_coin DESC 
    LIMIT 10
    ''')
    top_users = cursor.fetchall()
    
    conn.close()
    
    ranking_text = "🏆 <b>رنکینگ برترین‌ها</b>\n━━━━━━━━━━━━━━\n"
    
    for i, user in enumerate(top_users, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        username = user['username'] or user['full_name']
        ranking_text += f"{medal} {username}\n"
        ranking_text += f"   💰 {user['zone_coin']} ZC | 💎 {user['zone_gem']} ZG | ⚡ {user['zone_point']} ZP\n"
        ranking_text += f"   🎯 لول {user['level']}\n"
        if i < len(top_users):
            ranking_text += "━━━━━━\n"
    
    await message.answer(ranking_text)

@dp.message(F.text == "📖 راهنما")
async def cmd_help(message: Message):
    help_text = """
📖 <b>راهنمای کامل جنگ‌افزار</b>
━━━━━━━━━━━━━━
🎮 <b>دستورات اصلی:</b>
• /start - شروع بازی
• 👤 پروفایل - مشاهده پروفایل
• ⚔️ حمله - حمله به کاربران دیگر
• 🏪 بازار - خرید موشک و تجهیزات
• 🎁 باکس - خرید باکس‌های جایزه
• ⛏️ ماینر - سیستم ماینینگ ZP
• 🏰 دفاع - ارتقا سیستم دفاع
• 📊 رنکینگ - مشاهده رتبه‌ها
━━━━━━━━━━━━━━
💰 <b>ارزها:</b>
• ZC (Zone Coin) - سکه اصلی
• ZG (Zone Gem) - جم
• ZP (Zone Point) - امتیاز
━━━━━━━━━━━━━━
⚔️ <b>انواع حمله:</b>
1. حمله ساده - 1x damage
2. حمله متوسط - 1.5x damage  
3. حمله پیشرفته - 2x damage
4. حمله ویرانگر - 5x damage
━━━━━━━━━━━━━━
⛏️ <b>ماینر:</b>
• هر ساعت ZP تولید می‌کند
• با ارتقا تولید افزایش می‌یابد
• حداکثر 15 سطح
━━━━━━━━━━━━━━
🏰 <b>دفاع:</b>
• دفاع موشکی - کاهش 5% در هر سطح
• جنگ الکترونیک - کاهش 3% در هر سطح
• ضد جنگنده - کاهش 7% در هر سطح
━━━━━━━━━━━━━━
🎯 <b>نکات:</b>
• با حمله موفق XP دریافت می‌کنید
• با افزایش لول جایزه می‌گیرید
• از دفاع قوی برای محافظت استفاده کنید
• ماینر را به موقع ارتقا دهید
    """
    
    await message.answer(help_text)

# === دستورات ادمین ===
@dp.message(F.text == "👑 پنل ادمین")
async def cmd_admin_panel(message: Message):
    user_id = message.from_user.id
    
    if user_id not in ADMIN_IDS:
        await message.answer("❌ دسترسی denied!")
        return
    
        admin_text = """
👑 <b>پنل مدیریت ادمین</b>
━━━━━━━━━━━━━━
📊 آمار کامل - مشاهده آمار ربات
📢 پیام همگانی - ارسال پیام به همه
🎁 هدیه همگانی - دادن منابع به همه
➕ سکه - افزودن سکه به کاربر
💎 جم - افزودن جم به کاربر  
⚡ ZP - افزودن ZP به کاربر
📈 تغییر لول - تغییر لول کاربر
🔙 بازگشت - بازگشت به منوی اصلی
━━━━━━━━━━━━━━
⚠️ دسترسی فقط برای ادمین‌ها
    """
    
    await message.answer(admin_text, reply_markup=create_admin_keyboard())

@dp.message(F.text == "📊 آمار کامل")
async def cmd_admin_stats(message: Message):
    user_id = message.from_user.id
    
    if user_id not in ADMIN_IDS:
        await message.answer("❌ دسترسی denied!")
        return
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # آمار کلی
    cursor.execute('SELECT COUNT(*) as total_users FROM users')
    total_users = cursor.fetchone()['total_users']
    
    cursor.execute('SELECT COUNT(*) as total_attacks FROM attacks')
    total_attacks = cursor.fetchone()['total_attacks']
    
    cursor.execute('SELECT SUM(zone_coin) as total_coins FROM users')
    total_coins = cursor.fetchone()['total_coins'] or 0
    
    cursor.execute('SELECT SUM(zone_gem) as total_gems FROM users')
    total_gems = cursor.fetchone()['total_gems'] or 0
    
    cursor.execute('SELECT SUM(zone_point) as total_zp FROM users')
    total_zp = cursor.fetchone()['total_zp'] or 0
    
    # آخرین کاربران
    cursor.execute('''
    SELECT user_id, username, full_name, created_at 
    FROM users 
    ORDER BY created_at DESC 
    LIMIT 5
    ''')
    recent_users = cursor.fetchall()
    
    conn.close()
    
    stats_text = f"""
📊 <b>آمار کامل ربات</b>
━━━━━━━━━━━━━━
👥 تعداد کاربران: {total_users}
⚔️ تعداد حمله‌ها: {total_attacks}
━━━━━━━━━━━━━━
💰 کل سکه‌ها: {total_coins} ZC
💎 کل جم‌ها: {total_gems} ZG  
⚡ کل ZP: {total_zp}
━━━━━━━━━━━━━━
📅 <b>آخرین کاربران:</b>
    """
    
    for user in recent_users:
        date = datetime.fromtimestamp(user['created_at']).strftime('%Y/%m/%d')
        stats_text += f"\n• {user['full_name']} (@{user['username']}) - {date}"
    
    await message.answer(stats_text)

@dp.message(F.text == "📢 پیام همگانی")
async def cmd_broadcast(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if user_id not in ADMIN_IDS:
        await message.answer("❌ دسترسی denied!")
        return
    
    await message.answer("📝 لطفا پیام همگانی را ارسال کنید:")
    await state.set_state(UserStates.waiting_for_broadcast)

@dp.message(UserStates.waiting_for_broadcast)
async def process_broadcast(message: Message, state: FSMContext):
    broadcast_text = message.text
    
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    conn.close()
    
    success = 0
    failed = 0
    
    for user in users:
        try:
            await bot.send_message(user['user_id'], f"""
📢 <b>پیام همگانی از ادمین</b>
━━━━━━━━━━━━━━
{broadcast_text}
            """)
            success += 1
            await asyncio.sleep(0.1)  # جلوگیری از محدودیت
        except:
            failed += 1
    
    await message.answer(f"""
✅ <b>ارسال پیام همگانی</b>
━━━━━━━━━━━━━━
📤 ارسال شده به: {success} کاربر
❌ ناموفق: {failed} کاربر
📝 متن: {broadcast_text[:50]}...
    """)
    
    await state.clear()

@dp.message(F.text == "🎁 هدیه همگانی")
async def cmd_global_gift(message: Message):
    user_id = message.from_user.id
    
    if user_id not in ADMIN_IDS:
        await message.answer("❌ دسترسی denied!")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 1000 سکه به همه", callback_data="gift_all_coins_1000")],
        [InlineKeyboardButton(text="💎 10 جم به همه", callback_data="gift_all_gems_10")],
        [InlineKeyboardButton(text="⚡ 500 ZP به همه", callback_data="gift_all_zp_500")],
        [InlineKeyboardButton(text="🎁 همه موارد بالا", callback_data="gift_all_everything")]
    ])
    
    await message.answer("🎁 انتخاب هدیه همگانی:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("gift_all_"))
async def process_global_gift(callback: CallbackQuery):
    gift_type = callback.data.replace("gift_all_", "")
    
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    
    if gift_type == 'coins_1000':
        for user in users:
            db.update_user_coins(user['user_id'], 1000)
        gift_text = "1000 سکه"
    elif gift_type == 'gems_10':
        for user in users:
            db.update_user_gems(user['user_id'], 10)
        gift_text = "10 جم"
    elif gift_type == 'zp_500':
        for user in users:
            db.update_user_zp(user['user_id'], 500)
        gift_text = "500 ZP"
    elif gift_type == 'everything':
        for user in users:
            db.update_user_coins(user['user_id'], 1000)
            db.update_user_gems(user['user_id'], 10)
            db.update_user_zp(user['user_id'], 500)
        gift_text = "1000 سکه + 10 جم + 500 ZP"
    
    conn.close()
    
    await callback.message.edit_text(f"""
🎉 <b>هدیه همگانی ارسال شد!</b>
━━━━━━━━━━━━━━
🎁 هدیه: {gift_text}
👥 تعداد کاربران: {len(users)}
⏰ زمان: {datetime.now().strftime('%H:%M')}
    """)
    await callback.answer("✅ هدیه ارسال شد!")

@dp.message(F.text == "➕ سکه")
async def cmd_add_coins(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if user_id not in ADMIN_IDS:
        await message.answer("❌ دسترسی denied!")
        return
    
    await message.answer("🆔 آیدی کاربر + مقدار سکه (مثال: 123456 1000):")
    await state.set_state(UserStates.waiting_for_gift_amount)

@dp.message(F.text == "💎 جم")
async def cmd_add_gems(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if user_id not in ADMIN_IDS:
        await message.answer("❌ دسترسی denied!")
        return
    
    await message.answer("🆔 آیدی کاربر + مقدار جم (مثال: 123456 50):")
    await state.set_state(UserStates.waiting_for_gift_amount)

@dp.message(F.text == "⚡ ZP")
async def cmd_add_zp(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if user_id not in ADMIN_IDS:
        await message.answer("❌ دسترسی denied!")
        return
    
    await message.answer("🆔 آیدی کاربر + مقدار ZP (مثال: 123456 500):")
    await state.set_state(UserStates.waiting_for_gift_amount)

@dp.message(UserStates.waiting_for_gift_amount)
async def process_gift_amount(message: Message, state: FSMContext):
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer("❌ فرمت اشتباه! مثال: 123456 1000")
            return
        
        target_id = int(parts[0])
        amount = int(parts[1])
        
        target_user = db.get_user(target_id)
        if not target_user:
            await message.answer("❌ کاربر یافت نشد!")
            return
        
        # تشخیص نوع هدیه از متن قبلی
        state_data = await state.get_data()
        
        if "سکه" in message.reply_to_message.text:
            db.update_user_coins(target_id, amount)
            gift_type = "سکه"
            new_amount = target_user['zone_coin'] + amount
        elif "جم" in message.reply_to_message.text:
            db.update_user_gems(target_id, amount)
            gift_type = "جم"
            new_amount = target_user['zone_gem'] + amount
        elif "ZP" in message.reply_to_message.text:
            db.update_user_zp(target_id, amount)
            gift_type = "ZP"
            new_amount = target_user['zone_point'] + amount
        else:
            await message.answer("❌ نوع هدیه مشخص نیست!")
            return
        
        await message.answer(f"""
✅ <b>هدیه با موفقیت ارسال شد!</b>
━━━━━━━━━━━━━━
👤 کاربر: {target_user['full_name']}
🆔 آیدی: {target_id}
🎁 هدیه: {amount} {gift_type}
📊 مقدار جدید: {new_amount} {gift_type}
👤 ارسال‌کننده: {message.from_user.full_name}
        """)
        
        await state.clear()
        
    except ValueError:
        await message.answer("❌ مقادیر باید عدد باشند!")
    except Exception as e:
        logger.error(f"Gift error: {e}")
        await message.answer("❌ خطا در ارسال هدیه!")

@dp.message(F.text == "📈 تغییر لول")
async def cmd_change_level(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if user_id not in ADMIN_IDS:
        await message.answer("❌ دسترسی denied!")
        return
    
    await message.answer("🆔 آیدی کاربر + لول جدید (مثال: 123456 10):")
    await state.set_state(UserStates.waiting_for_gift_amount)

@dp.message(F.text == "🔙 بازگشت")
async def cmd_back_to_main(message: Message):
    await message.answer("🔙 بازگشت به منوی اصلی", reply_markup=create_main_keyboard())

@dp.callback_query(F.data == "back_to_main")
async def callback_back_to_main(callback: CallbackQuery):
    await callback.message.edit_text("🔙 بازگشت به منوی اصلی")
    await callback.message.answer("منوی اصلی:", reply_markup=create_main_keyboard())

# === Keep Alive برای Railway ===
async def keep_alive():
    """ارسال درخواست Keep-Alive"""
    if KEEP_ALIVE_URL:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(KEEP_ALIVE_URL) as resp:
                    logger.info(f"Keep-Alive sent: {resp.status}")
        except Exception as e:
            logger.error(f"Keep-Alive error: {e}")

# === وب سرور برای Railway ===
async def web_handler(request):
    """Handler اصلی وب‌سرور"""
    return web.Response(text="🤖 Warzone Bot is running!")

async def main():
    """تابع اصلی"""
    logger.info("Starting Warzone Bot...")
    
    # Keep-Alive دوره‌ای
    async def keep_alive_task():
        while True:
            await keep_alive()
            await asyncio.sleep(300)
    
    # شروع Keep-Alive
    asyncio.create_task(keep_alive_task())
    
    # راه‌اندازی وب‌سرور
    runner = web.AppRunner(web.Application())
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    
    # راه‌اندازی ربات
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
