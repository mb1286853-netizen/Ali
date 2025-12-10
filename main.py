#!/usr/bin/env python3
"""
Warzone Telegram Bot - Version 3.0.0
ربات جنگی کامل - با سیستم انتقام
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
    waiting_for_revenge = State()

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
            zone_gem INTEGER DEFAULT 0,
            zone_point INTEGER DEFAULT 500,
            level INTEGER DEFAULT 1,
            xp INTEGER DEFAULT 0,
            is_admin BOOLEAN DEFAULT 0,
            miner_level INTEGER DEFAULT 1,
            last_miner_claim INTEGER DEFAULT (strftime('%s', 'now')),
            cyber_tower_level INTEGER DEFAULT 0,
            defense_missile_level INTEGER DEFAULT 0,
            defense_electronic_level INTEGER DEFAULT 0,
            defense_antifighter_level INTEGER DEFAULT 0,
            total_defense_bonus REAL DEFAULT 0.0,
            fighter_level INTEGER DEFAULT 0,
            last_revenge_time INTEGER DEFAULT 0,
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
            missile_name TEXT,
            damage INTEGER,
            loot_coins INTEGER,
            loot_gems INTEGER,
            can_revenge BOOLEAN DEFAULT 1,
            revenge_taken BOOLEAN DEFAULT 0,
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
            (user_id, 'شبح', 5),
            (user_id, 'رعد', 3),
            (user_id, 'تندر', 1)
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
                WHEN 'شبح' THEN 1
                WHEN 'رعد' THEN 2
                WHEN 'تندر' THEN 3
                WHEN 'هاوک' THEN 4
                WHEN 'پاتریوت' THEN 5
                WHEN 'شهاب' THEN 6
                WHEN 'سیل' THEN 7
                WHEN 'توفان' THEN 8
                WHEN 'تایفون' THEN 9
                WHEN 'آپوکالیپس' THEN 10
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
                SET xp = ?, level = ?, zone_coin = zone_coin + 500
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
    
    def update_fighter_level(self, user_id: int, amount: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        UPDATE users 
        SET fighter_level = fighter_level + ? 
        WHERE user_id = ?
        ''', (amount, user_id))
        conn.commit()
        conn.close()
    
    def record_attack(self, attacker_id: int, target_id: int, missile_name: str, damage: int, loot_coins: int, loot_gems: int):
        """ثبت حمله در دیتابیس"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO attacks (attacker_id, target_id, missile_name, damage, loot_coins, loot_gems)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (attacker_id, target_id, missile_name, damage, loot_coins, loot_gems))
        attack_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return attack_id
    
    def get_recent_attacks_on_user(self, user_id: int, limit=5):
        """دریافت آخرین حملات بر روی کاربر"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        SELECT a.*, u.username, u.full_name 
        FROM attacks a
        JOIN users u ON a.attacker_id = u.user_id
        WHERE a.target_id = ? AND a.can_revenge = 1 AND a.revenge_taken = 0
        ORDER BY a.timestamp DESC
        LIMIT ?
        ''', (user_id, limit))
        attacks = cursor.fetchall()
        conn.close()
        return [dict(a) for a in attacks]
    
    def mark_revenge_taken(self, attack_id: int):
        """علامت‌گذاری انتقام گرفته شده"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE attacks SET revenge_taken = 1 WHERE id = ?', (attack_id,))
        conn.commit()
        conn.close()
    
    def update_last_revenge_time(self, user_id: int):
        """آپدیت زمان آخرین انتقام"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET last_revenge_time = ? WHERE user_id = ?', 
                      (int(time.time()), user_id))
        conn.commit()
        conn.close()

# === راه‌اندازی دیتابیس ===
db = Database()

# === داده‌های بازی ===
MISSILE_DATA = {
    # موشک‌های معمولی
    'شبح': {'damage': 25, 'price': 20, 'min_level': 1, 'type': 'normal'},
    'رعد': {'damage': 35, 'price': 50, 'min_level': 2, 'type': 'normal'},
    'تندر': {'damage': 45, 'price': 100, 'min_level': 3, 'type': 'normal'},
    'هاوک': {'damage': 55, 'price': 200, 'min_level': 4, 'type': 'normal'},
    'پاتریوت': {'damage': 65, 'price': 500, 'min_level': 5, 'type': 'normal'},
    
    # موشک‌های ویژه
    'شهاب': {'damage': 125, 'price': 2500, 'min_level': 6, 'type': 'special', 'gem_cost': 1},
    'سیل': {'damage': 150, 'price': 3000, 'min_level': 7, 'type': 'special', 'gem_cost': 2},
    'توفان': {'damage': 175, 'price': 3500, 'min_level': 8, 'type': 'special', 'gem_cost': 3},
    'تایفون': {'damage': 200, 'price': 4000, 'min_level': 9, 'type': 'special', 'gem_cost': 4},
    'آپوکالیپس': {'damage': 250, 'price': 5000, 'min_level': 10, 'type': 'special', 'gem_cost': 5}
}

MINER_LEVELS = {
    1: {'zp_per_hour': 50, 'upgrade_cost': 50},
    2: {'zp_per_hour': 100, 'upgrade_cost': 100},
    3: {'zp_per_hour': 150, 'upgrade_cost': 150},
    4: {'zp_per_hour': 200, 'upgrade_cost': 200},
    5: {'zp_per_hour': 250, 'upgrade_cost': 250},
    6: {'zp_per_hour': 300, 'upgrade_cost': 300},
    7: {'zp_per_hour': 350, 'upgrade_cost': 350},
    8: {'zp_per_hour': 400, 'upgrade_cost': 400},
    9: {'zp_per_hour': 450, 'upgrade_cost': 450},
    10: {'zp_per_hour': 500, 'upgrade_cost': 1000},
    11: {'zp_per_hour': 550, 'upgrade_cost': 1100},
    12: {'zp_per_hour': 600, 'upgrade_cost': 1200},
    13: {'zp_per_hour': 650, 'upgrade_cost': 1300},
    14: {'zp_per_hour': 700, 'upgrade_cost': 1400},
    15: {'zp_per_hour': 750, 'upgrade_cost': 5000}
}

FIGHTER_LEVELS = {
    0: {'damage_bonus': 0.0, 'defense_bonus': 0.0, 'upgrade_cost': 100},
    1: {'damage_bonus': 0.05, 'defense_bonus': 0.02, 'upgrade_cost': 200},
    2: {'damage_bonus': 0.10, 'defense_bonus': 0.04, 'upgrade_cost': 300},
    3: {'damage_bonus': 0.15, 'defense_bonus': 0.06, 'upgrade_cost': 400},
    4: {'damage_bonus': 0.20, 'defense_bonus': 0.08, 'upgrade_cost': 500},
    5: {'damage_bonus': 0.25, 'defense_bonus': 0.10, 'upgrade_cost': 1000},
    6: {'damage_bonus': 0.30, 'defense_bonus': 0.12, 'upgrade_cost': 1500},
    7: {'damage_bonus': 0.35, 'defense_bonus': 0.14, 'upgrade_cost': 2000},
    8: {'damage_bonus': 0.40, 'defense_bonus': 0.16, 'upgrade_cost': 2500},
    9: {'damage_bonus': 0.45, 'defense_bonus': 0.18, 'upgrade_cost': 3000},
    10: {'damage_bonus': 0.50, 'defense_bonus': 0.20, 'upgrade_cost': 5000}
}

# === توابع کمکی ===
def create_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 پروفایل"), KeyboardButton(text="⚔️ حمله")],
            [KeyboardButton(text="🏪 بازار"), KeyboardButton(text="🎁 باکس")],
            [KeyboardButton(text="⛏️ ماینر"), KeyboardButton(text="✈️ جنگنده")],
            [KeyboardButton(text="🏰 دفاع"), KeyboardButton(text="📊 رنکینگ")],
            [KeyboardButton(text="⚡ انتقام"), KeyboardButton(text="🆘 پشتیبانی")]
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
• ⚔️ سیستم حمله لول‌دار
• 🏪 بازار خرید موشک
• 🎁 باکس‌های مختلف
• ⛏️ سیستم ماینینگ دائم
• ✈️ سیستم جنگنده
• 🏰 سیستم دفاع
• ⚡ سیستم انتقام
• 📊 رنکینگ رقابتی

💰 دارایی اولیه:
• 1000 سکه
• 0 جم (جم فقط از باکس ویژه)  
• 500 ZP
• 5 موشک شبح
• 3 موشک رعد
• 1 موشک تندر

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
    
    # محاسبه ZP قابل دریافت از ماینر (همیشه)
    if user['last_miner_claim']:
        time_passed = int(time.time()) - user['last_miner_claim']
        zp_per_hour = MINER_LEVELS[user['miner_level']]['zp_per_hour']
        miner_zp = int((time_passed / 3600) * zp_per_hour)
    else:
        miner_zp = 0
    
    # دریافت موشک‌ها
    missiles = db.get_user_missiles(user_id)
    missiles_text = ""
    if missiles:
        for missile in missiles[:5]:
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
💰 سکه: {user['zone_coin']}
💎 جم: {user['zone_gem']}
⚡ امتیاز: {user['zone_point']} ZP
━━━━━━━━━━━━━━
⛏️ ماینر: لول {user['miner_level']}
📦 ZP قابل دریافت: {miner_zp}
━━━━━━━━━━━━━━
💣 موشک‌ها:
{missiles_text if missiles_text else "• هیچ موشکی ندارید!"}
━━━━━━━━━━━━━━
✈️ جنگنده: لول {user['fighter_level']}
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
async def cmd_attack(message: Message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await message.answer("❌ ابتدا با /start ثبت نام کنید!")
        return
    
    missiles = db.get_user_missiles(user_id)
    
    if not missiles:
        await message.answer("""
❌ <b>شما هیچ موشکی ندارید!</b>

🏪 برای خرید موشک به بازار بروید:
• شبح - 20 سکه
• رعد - 50 سکه
• تندر - 100 سکه
        """)
        return
    
    keyboard_buttons = []
    row = []
    
    for i, missile in enumerate(missiles):
        if i > 0 and i % 2 == 0:
            keyboard_buttons.append(row)
            row = []
        
        missile_name = missile['missile_name']
        quantity = missile['quantity']
        row.append(InlineKeyboardButton(
            text=f"{missile_name} ({quantity})", 
            callback_data=f"attack_with_{missile_name}"
        ))
    
    if row:
        keyboard_buttons.append(row)
    
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    attack_info = f"""
⚔️ <b>حمله لول‌دار</b>
━━━━━━━━━━━━━━
🎯 لول شما: {user['level']}

📝 <b>روش حمله:</b>
1. روی پیام کاربر مورد نظر <b>ریپلای (Reply)</b> کنید
2. سپس بنویسید: حمله با [نام موشک]

💡 <b>مثال:</b>
حمله با شبح

📊 <b>موشک‌های شما:</b>
    """
    
    await message.answer(attack_info, reply_markup=keyboard)

@dp.callback_query(F.data.startswith("attack_with_"))
async def process_attack_with_missile(callback: CallbackQuery):
    missile_name = callback.data.replace("attack_with_", "")
    
    missile_data = MISSILE_DATA.get(missile_name, {})
    damage = missile_data.get('damage', 0)
    
    await callback.message.edit_text(f"""
💣 <b>موشک انتخاب شد:</b> {missile_name}
💥 قدرت: {damage} آسیب

📝 <b>روش حمله:</b>
1. روی پیام کاربر مورد نظر <b>ریپلای (Reply)</b> کنید
2. سپس بنویسید: حمله با {missile_name}

⚠️ نکته: فقط می‌توانید به کاربرانی حمله کنید که در ربات ثبت‌نام کرده‌اند.
    """)
    
    await callback.answer()

@dp.message(F.text.startswith("حمله با"))
async def cmd_attack_with_missile(message: Message):
    if not message.reply_to_message:
        await message.answer("""
❌ <b>روش صحیح حمله:</b>
1. روی پیام کاربر مورد نظر <b>ریپلای (Reply)</b> کنید
2. سپس بنویسید: "حمله با [نام موشک]"

مثال: حمله با شبح
        """)
        return
    
    missile_name = message.text.replace("حمله با", "").strip()
    
    if not missile_name or missile_name not in MISSILE_DATA:
        await message.answer(f"""
❌ <b>موشک نامعتبر!</b>

موشک‌های معتبر:
• شبح • رعد • تندر • هاوک • پاتریوت
• شهاب • سیل • توفان • تایفون • آپوکالیپس

مثال: حمله با شبح
        """)
        return
    
    attacker_id = message.from_user.id
    attacker = db.get_user(attacker_id)
    
    if not attacker:
        await message.answer("❌ ابتدا با /start ثبت نام کنید!")
        return
    
    target_user = message.reply_to_message.from_user
    target_id = target_user.id
    
    if target_id == attacker_id:
        await message.answer("❌ نمی‌توانید به خود حمله کنید!")
        return
    
    target = db.get_user(target_id)
    if not target:
        await message.answer("❌ کاربر هدف در ربات ثبت‌نام نکرده است!")
        return
    
    missiles = db.get_user_missiles(attacker_id)
    missile_qty = next((m['quantity'] for m in missiles if m['missile_name'] == missile_name), 0)
    
    if missile_qty < 1:
        await message.answer(f"❌ {missile_name} کافی ندارید!")
        return
    
    await execute_missile_attack(attacker_id, target_id, missile_name, message)

async def execute_missile_attack(attacker_id: int, target_id: int, missile_name: str, message_obj):
    attacker = db.get_user(attacker_id)
    target = db.get_user(target_id)
    
    if not attacker or not target:
        await message_obj.answer("❌ کاربر یافت نشد!")
        return
    
    if attacker_id == target_id:
        await message_obj.answer("❌ نمی‌توانید به خود حمله کنید!")
        return
    
    missile_data = MISSILE_DATA.get(missile_name)
    
    if not missile_data:
        await message_obj.answer("❌ موشک نامعتبر!")
        return
    
    if attacker['level'] < missile_data['min_level']:
        await message_obj.answer(f"❌ برای این موشک حداقل لول {missile_data['min_level']} نیاز دارید!")
        return
    
    if missile_data['type'] == 'special' and missile_data.get('gem_cost', 0) > 0:
        if attacker['zone_gem'] < missile_data['gem_cost']:
            await message_obj.answer(f"❌ جم کافی ندارید! نیاز: {missile_data['gem_cost']} جم")
            return
    
    # محاسبه خسارت
    base_damage = missile_data['damage']
    fighter_bonus = FIGHTER_LEVELS.get(attacker['fighter_level'], {}).get('damage_bonus', 0)
    
    # بانس اضافی برای انتقام (اگر کاربر تحت حمله بوده)
    revenge_bonus = 0.0
    if target['last_revenge_time'] > 0:
        time_since_revenge = time.time() - target['last_revenge_time']
        if time_since_revenge < 3600:  # 1 ساعت
            revenge_bonus = 0.2  # 20% بانس اضافی
    
    actual_damage = int(base_damage * (1 + fighter_bonus + revenge_bonus) * (1 - target['total_defense_bonus']))
    
    # محاسبه غنیمت
    loot_coins = min(int(target['zone_coin'] * 0.10), 1000)
    loot_gems = min(int(target['zone_gem'] * 0.05), 5)
    
    # کسر و اضافه منابع
    new_target_coins = max(target['zone_coin'] - loot_coins, 0)
    new_target_gems = max(target['zone_gem'] - loot_gems, 0)
    
    db.update_user_coins(target_id, -loot_coins)
    db.update_user_gems(target_id, -loot_gems)
    db.update_user_coins(attacker_id, loot_coins)
    db.update_user_gems(attacker_id, loot_gems)
    
    # کسر موشک
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    UPDATE user_missiles 
    SET quantity = quantity - 1 
    WHERE user_id = ? AND missile_name = ?
    ''', (attacker_id, missile_name))
    conn.commit()
    conn.close()
    
    # کسر جم برای موشک‌های ویژه
    if missile_data['type'] == 'special' and missile_data.get('gem_cost', 0) > 0:
        db.update_user_gems(attacker_id, -missile_data['gem_cost'])
    
    # اضافه کردن XP
    xp_gained = missile_data['damage'] // 5
    level_up, new_level = db.add_xp(attacker_id, xp_gained)
    
    # ثبت حمله برای انتقام
    db.record_attack(attacker_id, target_id, missile_name, actual_damage, loot_coins, loot_gems)
    
    # ارسال گزارش
    bonus_text = ""
    if fighter_bonus > 0:
        bonus_text += f"\n✈️ بانس جنگنده: +{fighter_bonus*100:.0f}%"
    if revenge_bonus > 0:
        bonus_text += f"\n⚡ بانس انتقام: +{revenge_bonus*100:.0f}%"
    
    report_text = f"""
🎯 <b>حمله موفق!</b>
━━━━━━━━━━━━━━
⚔️ حمله‌کننده: {attacker['full_name']}
🎯 هدف: {target['full_name']}
💣 موشک: {missile_name}
💢 قدرت پایه: {missile_data['damage']} آسیب{bonus_text}
🛡️ کاهش دفاع: {target['total_defense_bonus']*100:.1f}%
💥 خسارت نهایی: {actual_damage}
━━━━━━━━━━━━━━
💰 غنیمت سکه: {loot_coins}
💎 غنیمت جم: {loot_gems}
⭐ XP کسب شده: {xp_gained}
{'🎉 سطح شما افزایش یافت!' if level_up else ''}
    """
    
    await message_obj.answer(report_text)
    
    # اطلاع به هدف با دکمه انتقام
    try:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚡ انتقام بگیر", callback_data=f"revenge_{attacker_id}")]
        ])
        
        target_report = f"""
🚨 <b>تحت حمله قرار گرفتید!</b>
━━━━━━━━━━━━━━
⚔️ حمله‌کننده: {attacker['full_name']}
💣 موشک: {missile_name}
💢 خسارت: {actual_damage}
💰 سکه از دست رفته: {loot_coins}
💎 جم از دست رفته: {loot_gems}
🛡️ دفاع شما {target['total_defense_bonus']*100:.1f}% خسارت را کاهش داد
━━━━━━━━━━━━━━
⚡ <b>شما می‌توانید انتقام بگیرید!</b>
• تا ۱ ساعت فرصت دارید
• ۲۰% بانس آسیب اضافی
• XP دو برابر
        """
        await bot.send_message(target_id, target_report, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Failed to send attack report to target: {e}")

@dp.message(F.text == "⚡ انتقام")
async def cmd_revenge(message: Message):
    """نمایش لیست حملات برای انتقام"""
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await message.answer("❌ ابتدا با /start ثبت نام کنید!")
        return
    
    # دریافت آخرین حملات
    recent_attacks = db.get_recent_attacks_on_user(user_id, limit=10)
    
    if not recent_attacks:
        await message.answer("""
📭 <b>هیچ حمله‌ای برای انتقام وجود ندارد!</b>

⚠️ شما می‌توانید فقط به حملات اخیر انتقام بگیرید:
• حداکثر ۱۰ حمله آخر
• فقط حملاتی که انتقام نگرفته‌اید
• تا ۲۴ ساعت پس از حمله
        """)
        return
    
    keyboard_buttons = []
    
    for attack in recent_attacks[:8]:  # حداکثر 8 حمله
        attacker_name = attack['full_name'] or attack['username'] or "ناشناس"
        time_ago = int(time.time()) - attack['timestamp']
        hours_ago = time_ago // 3600
        
        if hours_ago > 24:
            continue  # فقط حملات کمتر از 24 ساعت
        
        button_text = f"{attacker_name[:15]} - {hours_ago}ساعت پیش"
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"revenge_attack_{attack['id']}"
            )
        ])
    
    if not keyboard_buttons:
        await message.answer("⏳ تمام حملات قدیمی شده‌اند یا انتقام گرفته شده‌اند.")
        return
    
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    revenge_info = f"""
⚡ <b>لیست حملات برای انتقام</b>
━━━━━━━━━━━━━━
🎯 شما می‌توانید به {len(keyboard_buttons)-1} حمله انتقام بگیرید

💡 <b>مزایای انتقام:</b>
• ۲۰٪ آسیب بیشتر
• XP دو برابر
• رضایت روانی!

⚠️ <b>محدودیت‌ها:</b>
• فقط تا ۲۴ ساعت فرصت دارید
• هر حمله فقط یک بار انتقام
• نیاز به موشک دارید
        """
    
    await message.answer(revenge_info, reply_markup=keyboard)

@dp.callback_query(F.data.startswith("revenge_attack_"))
async def process_revenge_attack(callback: CallbackQuery):
    """پردازش انتخاب حمله برای انتقام"""
    attack_id = int(callback.data.replace("revenge_attack_", ""))
    
    # دریافت اطلاعات حمله
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT a.*, u.username, u.full_name 
    FROM attacks a
    JOIN users u ON a.attacker_id = u.user_id
    WHERE a.id = ? AND a.can_revenge = 1 AND a.revenge_taken = 0
    ''', (attack_id,))
    attack = cursor.fetchone()
    conn.close()
    
    if not attack:
        await callback.answer("❌ این حمله برای انتقام موجود نیست!")
        return
    
    attacker_name = attack['full_name'] or attack['username'] or "ناشناس"
    time_ago = int(time.time()) - attack['timestamp']
    hours_ago = time_ago // 3600
    
    if hours_ago > 24:
        await callback.answer("❌ زمان انتقام گذشته است (بیشتر از 24 ساعت)")
        return
    
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    
    # دریافت موشک‌های کاربر برای انتقام
    missiles = db.get_user_missiles(user_id)
    
    if not missiles:
        await callback.answer("❌ برای انتقام نیاز به موشک دارید!")
        return
    
    keyboard_buttons = []
    row = []
    
    for i, missile in enumerate(missiles):
        if i > 0 and i % 2 == 0:
            keyboard_buttons.append(row)
            row = []
        
        missile_name = missile['missile_name']
        quantity = missile['quantity']
        row.append(InlineKeyboardButton(
            text=f"{missile_name} ({quantity})", 
            callback_data=f"revenge_with_{attack_id}_{missile_name}"
        ))
    
    if row:
        keyboard_buttons.append(row)
    
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    revenge_text = f"""
⚡ <b>انتقام از:</b> {attacker_name}
🕐 زمان حمله: {hours_ago} ساعت پیش
💢 خسارت دریافتی: {attack['damage']} آسیب
💰 سکه از دست رفته: {attack['loot_coins']}
💎 جم از دست رفته: {attack['loot_gems']}

💣 <b>انتخاب موشک برای انتقام:</b>
    """
    
    await callback.message.edit_text(revenge_text, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data.startswith("revenge_with_"))
async def execute_revenge(callback: CallbackQuery):
    """انجام انتقام"""
    try:
        parts = callback.data.split("_")
        attack_id = int(parts[2])
        missile_name = parts[3]
        
        user_id = callback.from_user.id
        user = db.get_user(user_id)
        
        if not user:
            await callback.answer("❌ کاربر یافت نشد!")
            return
        
        # دریافت اطلاعات حمله اصلی
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        SELECT a.*, u.username, u.full_name 
        FROM attacks a
        JOIN users u ON a.attacker_id = u.user_id
        WHERE a.id = ? AND a.can_revenge = 1 AND a.revenge_taken = 0
        ''', (attack_id,))
        original_attack = cursor.fetchone()
        conn.close()
        
        if not original_attack:
            await callback.answer("❌ این حمله برای انتقام موجود نیست!")
            return
        
        attacker_id = original_attack['attacker_id']
        attacker = db.get_user(attacker_id)
        
        if not attacker:
            await callback.answer("❌ حمله‌کننده یافت نشد!")
            return
        
        # بررسی موجودی موشک
        missiles = db.get_user_missiles(user_id)
        missile_qty = next((m['quantity'] for m in missiles if m['missile_name'] == missile_name), 0)
        
        if missile_qty < 1:
            await callback.answer(f"❌ {missile_name} کافی ندارید!")
            return
        
        missile_data = MISSILE_DATA.get(missile_name)
        
        if not missile_data:
            await callback.answer("❌ موشک نامعتبر!")
            return
        
        # محاسبه خسارت انتقام (20% بیشتر + بانس جنگنده)
        base_damage = missile_data['damage']
        fighter_bonus = FIGHTER_LEVELS.get(user['fighter_level'], {}).get('damage_bonus', 0)
        revenge_bonus = 0.2  # 20% بانس انتقام
        
        actual_damage = int(base_damage * (1 + fighter_bonus + revenge_bonus) * (1 - attacker['total_defense_bonus']))
        
        # محاسبه غنیمت (50% بیشتر از معمول)
        loot_coins = min(int(attacker['zone_coin'] * 0.15), 1500)  # 15% به جای 10%
        loot_gems = min(int(attacker['zone_gem'] * 0.075), 8)      # 7.5% به جای 5%
        
        # کسر و اضافه منابع
        new_attacker_coins = max(attacker['zone_coin'] - loot_coins, 0)
        new_attacker_gems = max(attacker['zone_gem'] - loot_gems, 0)
        
        db.update_user_coins(attacker_id, -loot_coins)
        db.update_user_gems(attacker_id, -loot_gems)
        db.update_user_coins(user_id, loot_coins)
        db.update_user_gems(user_id, loot_gems)
        
        # کسر موشک
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        UPDATE user_missiles 
        SET quantity = quantity - 1 
        WHERE user_id = ? AND missile_name = ?
        ''', (user_id, missile_name))
        conn.commit()
        conn.close()
        
        # کسر جم برای موشک‌های ویژه
        if missile_data['type'] == 'special' and missile_data.get('gem_cost', 0) > 0:
            db.update_user_gems(user_id, -missile_data['gem_cost'])
        
        # اضافه کردن XP (دو برابر)
        xp_gained = (missile_data['damage'] // 5) * 2
        level_up, new_level = db.add_xp(user_id, xp_gained)
        
        # علامت‌گذاری انتقام گرفته شده
        db.mark_revenge_taken(attack_id)
        db.update_last_revenge_time(user_id)
        
        # ارسال گزارش
        report_text = f"""
⚡ <b>انتقام موفق!</b>
━━━━━━━━━━━━━━
🎯 انتقام‌گیرنده: {user['full_name']}
⚔️ هدف: {attacker['full_name']}
💣 موشک: {missile_name}
💢 قدرت پایه: {missile_data['damage']} آسیب
✈️ بانس جنگنده: +{fighter_bonus*100:.0f}%
⚡ بانس انتقام: +{revenge_bonus*100:.0f}%
🛡️ کاهش دفاع: {attacker['total_defense_bonus']*100:.1f}%
💥 خسارت نهایی: {actual_damage}
━━━━━━━━━━━━━━
💰 غنیمت سکه: {loot_coins} (50% بیشتر)
💎 غنیمت جم: {loot_gems} (50% بیشتر)
⭐ XP کسب شده: {xp_gained} (دو برابر)
{'🎉 سطح شما افزایش یافت!' if level_up else ''}
━━━━━━━━━━━━━━
✅ انتقام شما ثبت شد و هدف مطلع خواهد شد.
        """
        
        await callback.message.edit_text(report_text)
        await callback.answer("✅ انتقام با موفقیت انجام شد!")
        
        # اطلاع به هدف انتقام
        try:
            target_report = f"""
⚡ <b>از شما انتقام گرفته شد!</b>
━━━━━━━━━━━━━━
🎯 انتقام‌گیرنده: {user['full_name']}
💢 خسارت: {actual_damage}
💰 سکه از دست رفته: {loot_coins}
💎 جم از دست رفته: {loot_gems}
📊 موجودی جدید:
• سکه: {new_attacker_coins}
• جم: {new_attacker_gems}
━━━━━━━━━━━━━━
⚠️ این انتقام برای حمله شما به {user['full_name']} بود.
            """
            await bot.send_message(attacker_id, target_report)
        except Exception as e:
            logger.error(f"Failed to send revenge report to target: {e}")
    
    except Exception as e:
        logger.error(f"Revenge error: {e}")
        await callback.answer("❌ خطا در انجام انتقام!")

@dp.callback_query(F.data.startswith("revenge_"))
async def quick_revenge(callback: CallbackQuery):
    """انتقام سریع از پیام حمله"""
    try:
        attacker_id = int(callback.data.replace("revenge_", ""))
        user_id = callback.from_user.id
        
        # بررسی اینکه آیا حمله اخیرا اتفاق افتاده
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        SELECT * FROM attacks 
        WHERE attacker_id = ? AND target_id = ? 
        ORDER BY timestamp DESC 
        LIMIT 1
        ''', (attacker_id, user_id))
        recent_attack = cursor.fetchone()
        conn.close()
        
        if not recent_attack:
            await callback.answer("❌ حمله‌ای برای انتقام پیدا نشد!")
            return
        
        # ادامه مانند انتقام معمولی
        await execute_revenge_from_attack(user_id, attacker_id, recent_attack['id'], callback)
        
    except Exception as e:
        logger.error(f"Quick revenge error: {e}")
        await callback.answer("❌ خطا در انتقام سریع!")

async def execute_revenge_from_attack(user_id: int, attacker_id: int, attack_id: int, callback: CallbackQuery):
    """انجام انتقام از یک حمله خاص"""
    user = db.get_user(user_id)
    attacker = db.get_user(attacker_id)
    
    if not user or not attacker:
        await callback.answer("❌ کاربر یافت نشد!")
        return
    
    # دریافت موشک‌های کاربر
    missiles = db.get_user_missiles(user_id)
    
    if not missiles:
        await callback.answer("❌ برای انتقام نیاز به موشک دارید!")
        return
    
    keyboard_buttons = []
    row = []
    
    for i, missile in enumerate(missiles[:8]):  # حداکثر 8 موشک
        if i > 0 and i % 2 == 0:
            keyboard_buttons.append(row)
            row = []
        
        missile_name = missile['missile_name']
        quantity = missile['quantity']
        row.append(InlineKeyboardButton(
            text=f"{missile_name} ({quantity})", 
            callback_data=f"revenge_with_{attack_id}_{missile_name}"
        ))
    
    if row:
        keyboard_buttons.append(row)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    revenge_text = f"""
⚡ <b>انتقام سریع</b>
━━━━━━━━━━━━━━
🎯 هدف: {attacker['full_name']}
💢 خسارت دریافتی: اخیراً

💣 <b>انتخاب موشک برای انتقام:</b>
• ۲۰٪ آسیب بیشتر
• XP دو برابر
• رضایت کامل!
    """
    
    await callback.message.edit_text(revenge_text, reply_markup=keyboard)
    await callback.answer()

@dp.message(F.text == "🏪 بازار")
async def cmd_market(message: Message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await message.answer("❌ ابتدا با /start ثبت نام کنید!")
        return
    
    user_missiles = db.get_user_missiles(user_id)
    user_missiles_dict = {m['missile_name']: m['quantity'] for m in user_missiles}
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="شبح", callback_data="buy_ghost"),
            InlineKeyboardButton(text="رعد", callback_data="buy_thunder")
        ],
        [
            InlineKeyboardButton(text="تندر", callback_data="buy_boomer"),
            InlineKeyboardButton(text="هاوک", callback_data="buy_hawk")
        ],
        [
            InlineKeyboardButton(text="پاتریوت", callback_data="buy_patriot"),
            InlineKeyboardButton(text="⏩ ویژه", callback_data="market_special")
        ],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")]
    ])
    
    missiles_text = ""
    common_missiles = ['شبح', 'رعد', 'تندر']
    for missile_name in common_missiles:
        qty = user_missiles_dict.get(missile_name, 0)
        missiles_text += f"• {missile_name}: {qty} عدد\n"
    
    market_text = f"""
🏪 <b>بازار جنگ‌افزار</b>
━━━━━━━━━━━━━━
💰 سکه شما: {user['zone_coin']}
💎 جم شما: {user['zone_gem']}
🎯 لول: {user['level']}
━━━━━━━━━━━━━━
📊 <b>موشک‌های شما:</b>
{missiles_text if missiles_text else "• هیچ موشکی ندارید!"}
━━━━━━━━━━━━━━
📦 <b>موشک‌های معمولی:</b>

1. شبح
   • قدرت: 25 آسیب
   • قیمت: 20 سکه
   • نیاز لول: 1

2. رعد
   • قدرت: 35 آسیب  
   • قیمت: 50 سکه
   • نیاز لول: 2

3. تندر
   • قدرت: 45 آسیب
   • قیمت: 100 سکه
   • نیاز لول: 3

4. هاوک
   • قدرت: 55 آسیب
   • قیمت: 200 سکه
   • نیاز لول: 4

5. پاتریوت
   • قدرت: 65 آسیب
   • قیمت: 500 سکه
   • نیاز لول: 5
    """
    
    await message.answer(market_text, reply_markup=keyboard)

@dp.callback_query(F.data == "market_special")
async def cmd_market_special(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="شهاب", callback_data="buy_meteor"),
            InlineKeyboardButton(text="سیل", callback_data="buy_tsunami")
        ],
        [
            InlineKeyboardButton(text="توفان", callback_data="buy_storm"),
            InlineKeyboardButton(text="تایفون", callback_data="buy_typhoon")
        ],
        [
            InlineKeyboardButton(text="آپوکالیپس", callback_data="buy_apocalypse"),
            InlineKeyboardButton(text="⏪ معمولی", callback_data="market_normal")
        ]
    ])
    
    special_text = f"""
💎 <b>موشک‌های ویژه</b>
━━━━━━━━━━━━━━
💰 سکه شما: {user['zone_coin']}
💎 جم شما: {user['zone_gem']}
🎯 لول: {user['level']}
━━━━━━━━━━━━━━
💣 <b>موشک‌های ویژه:</b>

1. شهاب
   • قدرت: 125 آسیب
   • قیمت: 2,500 سکه + 1 جم
   • نیاز لول: 6

2. سیل
   • قدرت: 150 آسیب
   • قیمت: 3,000 سکه + 2 جم
   • نیاز لول: 7

3. توفان
   • قدرت: 175 آسیب  
   • قیمت: 3,500 سکه + 3 جم
   • نیاز لول: 8

4. تایفون
   • قدرت: 200 آسیب
   • قیمت: 4,000 سکه + 4 جم
   • نیاز لول: 9

5. آپوکالیپس
   • قدرت: 250 آسیب
   • قیمت: 5,000 سکه + 5 جم
   • نیاز لول: 10
    """
    
    await callback.message.edit_text(special_text, reply_markup=keyboard)

@dp.callback_query(F.data == "market_normal")
async def cmd_market_normal(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="شبح", callback_data="buy_ghost"),
            InlineKeyboardButton(text="رعد", callback_data="buy_thunder")
        ],
        [
            InlineKeyboardButton(text="تندر", callback_data="buy_boomer"),
            InlineKeyboardButton(text="هاوک", callback_data="buy_hawk")
        ],
        [
            InlineKeyboardButton(text="پاتریوت", callback_data="buy_patriot"),
            InlineKeyboardButton(text="⏩ ویژه", callback_data="market_special")
        ]
    ])
    
    market_text = f"""
🏪 <b>بازار جنگ‌افزار</b>
━━━━━━━━━━━━━━
💰 سکه شما: {user['zone_coin']}
💎 جم شما: {user['zone_gem']}
🎯 لول: {user['level']}
━━━━━━━━━━━━━━
📦 <b>موشک‌های معمولی:</b>

1. شبح - 20 سکه
2. رعد - 50 سکه  
3. تندر - 100 سکه
4. هاوک - 200 سکه
5. پاتریوت - 500 سکه
    """
    
    await callback.message.edit_text(market_text, reply_markup=keyboard)

@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: CallbackQuery):
    missile_type = callback.data.replace("buy_", "")
    
    missile_map = {
        'ghost': 'شبح',
        'thunder': 'رعد',
        'boomer': 'تندر',
        'hawk': 'هاوک',
        'patriot': 'پاتریوت',
        'meteor': 'شهاب',
        'tsunami': 'سیل',
        'storm': 'توفان',
        'typhoon': 'تایفون',
        'apocalypse': 'آپوکالیپس'
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
    
    if user['level'] < missile_data['min_level']:
        await callback.answer(f"❌ نیاز به لول {missile_data['min_level']} دارید! (لول شما: {user['level']})")
        return
    
    if user['zone_coin'] < missile_data['price']:
        await callback.answer(f"❌ سکه کافی ندارید! نیاز: {missile_data['price']} سکه")
        return
    
    if missile_data['type'] == 'special' and missile_data.get('gem_cost', 0) > 0:
        if user['zone_gem'] < missile_data['gem_cost']:
            await callback.answer(f"❌ جم کافی ندارید! نیاز: {missile_data['gem_cost']} جم")
            return
    
    db.update_user_coins(user_id, -missile_data['price'])
    
    if missile_data['type'] == 'special' and missile_data.get('gem_cost', 0) > 0:
        db.update_user_gems(user_id, -missile_data['gem_cost'])
    
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
    
    gem_text = f" + {missile_data['gem_cost']} جم" if missile_data.get('gem_cost', 0) > 0 else ""
    
    report_text = f"""
✅ <b>خرید موفق!</b>
━━━━━━━━━━━━━━
📦 آیتم: {missile_name}
💰 قیمت: {missile_data['price']} سکه{gem_text}
💥 قدرت: {missile_data['damage']} آسیب
🎯 نیاز لول: {missile_data['min_level']}
━━━━━━━━━━━━━━
💰 سکه باقی‌مانده: {user['zone_coin'] - missile_data['price']}
💎 جم باقی‌مانده: {user['zone_gem'] - missile_data.get('gem_cost', 0)}
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
            InlineKeyboardButton(text="🎁 باکس سکه (50 سکه)", callback_data="box_coin"),
            InlineKeyboardButton(text="🎁 باکس ZP (100 سکه)", callback_data="box_zp")
        ],
        [
            InlineKeyboardButton(text="💎 باکس ویژه (2 جم)", callback_data="box_special"),
            InlineKeyboardButton(text="👑 باکس افسانه‌ای (5 جم)", callback_data="box_legendary")
        ],
        [
            InlineKeyboardButton(text="🆓 باکس رایگان", callback_data="box_free"),
            InlineKeyboardButton(text="📦 موجودی", callback_data="box_inventory")
        ],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")]
    ])
    
    box_text = f"""
🎁 <b>فروشگاه باکس‌ها</b>
━━━━━━━━━━━━━━
💰 سکه شما: {user['zone_coin']}
💎 جم شما: {user['zone_gem']}
⚡ ZP شما: {user['zone_point']}
━━━━━━━━━━━━━━
🎰 شانس خود را امتحان کنید!

1. 🎁 <b>باکس سکه</b>
   • قیمت: 50 سکه
   • جایزه: 10-200 سکه
   
2. 🎁 <b>باکس ZP</b>
   • قیمت: 100 سکه
   • جایزه: 25-100 ZP

3. 💎 <b>باکس ویژه</b>
   • قیمت: 2 جم
   • جایزه: موشک‌های ویژه

4. 👑 <b>باکس افسانه‌ای</b>
   • قیمت: 5 جم
   • جایزه: ترکیبی (شانس 10%)

5. 🆓 <b>باکس رایگان</b>
   • قیمت: رایگان
   • جایزه: 5-50 (تصادفی)
   • بدون کوئلتایم!
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
        'coin': {'min': 10, 'max': 200, 'cost_coin': 50, 'cost_gem': 0},
        'zp': {'min': 25, 'max': 100, 'cost_coin': 100, 'cost_gem': 0},
        'special': {'min': 1, 'max': 3, 'cost_coin': 0, 'cost_gem': 2, 'type': 'missile'},
        'legendary': {'min': 100, 'max': 1000, 'cost_coin': 0, 'cost_gem': 5, 'type': 'mixed'},
        'free': {'min': 5, 'max': 50, 'cost_coin': 0, 'cost_gem': 0}
    }
    
    if box_type not in rewards:
        await callback.answer("❌ باکس نامعتبر!")
        return
    
    reward = rewards[box_type]
    
    if box_type != 'free':
        if user['zone_coin'] < reward['cost_coin']:
            await callback.answer("❌ سکه کافی ندارید!")
            return
        
        if user['zone_gem'] < reward['cost_gem']:
            await callback.answer("❌ جم کافی ندارید!")
            return
    
    if reward['cost_coin'] > 0:
        db.update_user_coins(user_id, -reward['cost_coin'])
    if reward['cost_gem'] > 0:
        db.update_user_gems(user_id, -reward['cost_gem'])
    
    prize_text = ""
    prize_value = 0
    
    if box_type == 'free':
        prize = random.randint(reward['min'], reward['max'])
        prize_type = random.choice(['coin', 'zp', 'missile'])
        
        if prize_type == 'coin':
            db.update_user_coins(user_id, prize)
            prize_text = f"{prize} سکه"
            prize_value = prize
        elif prize_type == 'zp':
            db.update_user_zp(user_id, prize)
            prize_text = f"{prize} ZP"
            prize_value = prize
        else:
            # جایزه موشک رایگان
            free_missiles = ['شبح', 'رعد', 'تندر']
            missile = random.choice(free_missiles)
            qty = random.randint(1, 3)
            
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
            INSERT INTO user_missiles (user_id, missile_name, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, missile_name) 
            DO UPDATE SET quantity = quantity + ?
            ''', (user_id, missile, qty, qty))
            conn.commit()
            conn.close()
            
            prize_text = f"{qty} عدد {missile}"
            prize_value = MISSILE_DATA[missile]['price'] * qty
    
    elif box_type == 'special':
        special_missiles = ['شهاب', 'سیل', 'توفان']
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
        if random.random() < 0.1:
            prize = random.randint(500, 2000)
            db.update_user_coins(user_id, prize)
            prize_text = f"🎉 جکپات! {prize} سکه"
            prize_value = prize
        else:
            prize = random.randint(reward['min'], reward['max'])
            db.update_user_coins(user_id, prize)
            prize_text = f"{prize} سکه"
            prize_value = prize
    
    else:
        prize = random.randint(reward['min'], reward['max'])
        if box_type == 'coin':
            db.update_user_coins(user_id, prize)
            prize_text = f"{prize} سکه"
            prize_value = prize
        else:
            db.update_user_zp(user_id, prize)
            prize_text = f"{prize} ZP"
            prize_value = prize
    
    box_names = {
        'coin': 'باکس سکه',
        'zp': 'باکس ZP',
        'special': 'باکس ویژه',
        'legendary': 'باکس افسانه‌ای',
        'free': 'باکس رایگان'
    }
    
    report_text = f"""
🎉 <b>باکس باز شد!</b>
━━━━━━━━━━━━━━
🎁 نوع باکس: {box_names[box_type]}
🎰 جایزه: {prize_text}
💰 ارزش تقریبی: {prize_value} سکه
━━━━━━━━━━━━━━
💰 سکه فعلی: {user['zone_coin'] - reward['cost_coin'] + (prize if box_type == 'coin' or box_type == 'legendary' else 0)}
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
    
    miner_zp = 0
    if user['last_miner_claim']:
        time_passed = int(time.time()) - user['last_miner_claim']
        if time_passed > 0:
            zp_per_hour = MINER_LEVELS[user['miner_level']]['zp_per_hour']
            miner_zp = int((time_passed / 3600) * zp_per_hour)
    
    keyboard_buttons = []
    
    # دکمه برداشت همیشه نمایش داده می‌شود
    keyboard_buttons.append([InlineKeyboardButton(text=f"📦 برداشت {miner_zp} ZP", callback_data="claim_miner")])
    
    current_level = user['miner_level']
    if current_level < 15:
        upgrade_cost = MINER_LEVELS[current_level]['upgrade_cost']
        keyboard_buttons.append([InlineKeyboardButton(text=f"⬆️ ارتقا به لول {current_level + 1}", callback_data="upgrade_miner")])
    
    keyboard_buttons.append([InlineKeyboardButton(text="📊 اطلاعات ماینر", callback_data="miner_info")])
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    last_claim_time = "هرگز"
    if user['last_miner_claim']:
        last_claim_time = datetime.fromtimestamp(user['last_miner_claim']).strftime('%H:%M')
    
    next_level_info = ""
    if current_level < 15:
        next_level = current_level + 1
        next_zp = MINER_LEVELS[next_level]['zp_per_hour']
        next_cost = MINER_LEVELS[current_level]['upgrade_cost']
        next_level_info = f"""
📈 سطح بعدی: {next_level}
⚡ تولید بعدی: {next_zp} ZP/ساعت
💰 هزینه ارتقا: {next_cost} سکه
        """
    else:
        next_level_info = "🎉 شما به ماکس لول رسیده‌اید!"
    
    miner_text = f"""
⛏️ <b>سیستم ماینینگ</b>
━━━━━━━━━━━━━━
📊 سطح ماینر: {current_level}
⚡ تولید در ساعت: {MINER_LEVELS[current_level]['zp_per_hour']} ZP
💰 هزینه ارتقا فعلی: {MINER_LEVELS[current_level]['upgrade_cost']} سکه
━━━━━━━━━━━━━━
📦 ZP قابل برداشت: {miner_zp}
⏰ آخرین برداشت: {last_claim_time}
⏳ زمان سپری شده: {time_passed // 3600 if user['last_miner_claim'] else 0} ساعت
━━━━━━━━━━━━━━
{next_level_info}
━━━━━━━━━━━━━━
💰 سکه شما: {user['zone_coin']}
    """
    
    await message.answer(miner_text, reply_markup=keyboard)

@dp.callback_query(F.data == "claim_miner")
async def process_claim_miner(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await callback.answer("❌ کاربر یافت نشد!")
        return
    
    miner_zp = 0
    if user['last_miner_claim']:
        time_passed = int(time.time()) - user['last_miner_claim']
        if time_passed > 0:
            zp_per_hour = MINER_LEVELS[user['miner_level']]['zp_per_hour']
            miner_zp = int((time_passed / 3600) * zp_per_hour)
    
    if miner_zp <= 0:
        await callback.answer("❌ هنوز ZP جدیدی تولید نشده!")
        return
    
    db.update_user_zp(user_id, miner_zp)
    
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET last_miner_claim = ? WHERE user_id = ?', 
                  (int(time.time()), user_id))
    conn.commit()
    conn.close()
    
    await callback.message.edit_text(f"""
✅ <b>برداشت موفق!</b>
━━━━━━━━━━━━━━
⛏️ ZP برداشت شده: {miner_zp}
💰 ZP کل: {user['zone_point'] + miner_zp} ZP
⏰ زمان برداشت: {datetime.now().strftime('%H:%M')}
━━━━━━━━━━━━━━
⚡ ماینر دوباره شروع به کار کرد!
📊 تولید فعلی: {MINER_LEVELS[user['miner_level']]['zp_per_hour']} ZP/ساعت
    """)
    await callback.answer(f"✅ {miner_zp} ZP برداشت شد!")

@dp.callback_query(F.data == "upgrade_miner")
async def process_upgrade_miner(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await callback.answer("❌ کاربر یافت نشد!")
        return
    
    current_level = user['miner_level']
    
    if current_level >= 15:
        await callback.answer("🎉 ماینر شما در ماکس لول است!")
        return
    
    upgrade_cost = MINER_LEVELS[current_level]['upgrade_cost']
    
    if user['zone_coin'] < upgrade_cost:
        await callback.answer(f"❌ سکه کافی ندارید! نیاز: {upgrade_cost} سکه")
        return
    
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
💰 هزینه پرداختی: {upgrade_cost} سکه
━━━━━━━━━━━━━━
💰 سکه باقی‌مانده: {user['zone_coin'] - upgrade_cost} سکه
🎉 ماینر شما با قدرت بیشتر کار می‌کند!

📊 <b>آینده:</b>
• سطح بعدی: {new_level + 1 if new_level < 15 else 'ماکس'}
• هزینه بعدی: {MINER_LEVELS.get(new_level, {}).get('upgrade_cost', 'ماکس')} سکه
    """)
    await callback.answer(f"✅ ماینر به سطح {new_level} ارتقا یافت!")

@dp.message(F.text == "✈️ جنگنده")
async def cmd_fighter(message: Message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await message.answer("❌ ابتدا با /start ثبت نام کنید!")
        return
    
    current_level = user['fighter_level']
    fighter_data = FIGHTER_LEVELS.get(current_level, {})
    next_level_data = FIGHTER_LEVELS.get(current_level + 1, {})
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"⬆️ ارتقا جنگنده", callback_data="upgrade_fighter"),
            InlineKeyboardButton(text="📊 اطلاعات", callback_data="fighter_info")
        ],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")]
    ])
    
    fighter_text = f"""
✈️ <b>سیستم جنگنده</b>
━━━━━━━━━━━━━━
📊 سطح جنگنده: {current_level}
💥 بانس آسیب: +{fighter_data.get('damage_bonus', 0)*100:.0f}%
🛡️ بانس دفاع: +{fighter_data.get('defense_bonus', 0)*100:.0f}%
    """
    
    if current_level < 10:
        fighter_text += f"""
━━━━━━━━━━━━━━
📈 سطح بعدی: {current_level + 1}
💥 بانس آسیب بعدی: +{next_level_data.get('damage_bonus', 0)*100:.0f}%
🛡️ بانس دفاع بعدی: +{next_level_data.get('defense_bonus', 0)*100:.0f}%
💰 هزینه ارتقا: {next_level_data.get('upgrade_cost', 0)} سکه
        """
    else:
        fighter_text += "\n\n🎉 شما به ماکس لول جنگنده رسیده‌اید!"
    
    fighter_text += f"""
━━━━━━━━━━━━━━
💰 سکه شما: {user['zone_coin']}
    """
    
    await message.answer(fighter_text, reply_markup=keyboard)

@dp.callback_query(F.data == "upgrade_fighter")
async def process_upgrade_fighter(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await callback.answer("❌ کاربر یافت نشد!")
        return
    
    current_level = user['fighter_level']
    
    if current_level >= 10:
        await callback.answer("🎉 جنگنده شما در ماکس لول است!")
        return
    
    next_level_data = FIGHTER_LEVELS.get(current_level + 1, {})
    upgrade_cost = next_level_data.get('upgrade_cost', 0)
    
    if user['zone_coin'] < upgrade_cost:
        await callback.answer(f"❌ سکه کافی ندارید! نیاز: {upgrade_cost} سکه")
        return
    
    db.update_user_coins(user_id, -upgrade_cost)
    db.update_fighter_level(user_id, 1)
    
    new_level = current_level + 1
    new_data = FIGHTER_LEVELS.get(new_level, {})
    
    await callback.message.edit_text(f"""
✈️ <b>ارتقا موفق!</b>
━━━━━━━━━━━━━━
📊 سطح جدید: {new_level}
💥 بانس آسیب جدید: +{new_data.get('damage_bonus', 0)*100:.0f}%
🛡️ بانس دفاع جدید: +{new_data.get('defense_bonus', 0)*100:.0f}%
💰 هزینه پرداختی: {upgrade_cost} سکه
━━━━━━━━━━━━━━
💰 سکه باقی‌مانده: {user['zone_coin'] - upgrade_cost} سکه
🎉 جنگنده شما قوی‌تر شد!

📊 <b>تاثیر:</b>
• حمله‌های شما {new_data.get('damage_bonus', 0)*100:.0f}% قوی‌تر
• دفاع شما {new_data.get('defense_bonus', 0)*100:.0f}% بهتر
    """)
    await callback.answer(f"✅ جنگنده به سطح {new_level} ارتقا یافت!")

@dp.message(F.text == "🏰 دفاع")
async def cmd_defense(message: Message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await message.answer("❌ ابتدا با /start ثبت نام کنید!")
        return
    
    # محاسبه بانس دفاع کل
    total_defense_bonus = (user['defense_missile_level'] * 0.05) + \
                         (user['defense_electronic_level'] * 0.03) + \
                         (user['defense_antifighter_level'] * 0.07)
    total_defense_bonus = min(total_defense_bonus, 0.5)  # حداکثر 50%
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚀 دفاع موشکی", callback_data="upgrade_missile_def"),
            InlineKeyboardButton(text="📡 جنگ الکترونیک", callback_data="upgrade_electronic_def")
        ],
        [
            InlineKeyboardButton(text="✈️ ضد جنگنده", callback_data="upgrade_antifighter_def"),
            InlineKeyboardButton(text="📊 اطلاعات دفاع", callback_data="defense_info")
        ],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")]
    ])
    
    defense_text = f"""
🏰 <b>سیستم دفاع</b>
━━━━━━━━━━━━━━
🛡️ بانس دفاع کلی: {total_defense_bonus*100:.1f}%
━━━━━━━━━━━━━━
🚀 <b>دفاع موشکی</b>
   • لول: {user['defense_missile_level']}
   • بانس: {user['defense_missile_level'] * 5}%
   • هزینه ارتقا: {(user['defense_missile_level'] + 1) * 100} سکه

📡 <b>جنگ الکترونیک</b>
   • لول: {user['defense_electronic_level']}
   • بانس: {user['defense_electronic_level'] * 3}%
   • هزینه ارتقا: {(user['defense_electronic_level'] + 1) * 80} سکه

✈️ <b>ضد جنگنده</b>
   • لول: {user['defense_antifighter_level']}
   • بانس: {user['defense_antifighter_level'] * 7}%
   • هزینه ارتقا: {(user['defense_antifighter_level'] + 1) * 120} سکه
━━━━━━━━━━━━━━
💰 سکه شما: {user['zone_coin']}
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
    
    current_level = 0
    cost_multiplier = 0
    defense_name = ""
    
    if defense_type == 'missile':
        current_level = user['defense_missile_level']
        cost_multiplier = 100
        defense_name = "دفاع موشکی"
    elif defense_type == 'electronic':
        current_level = user['defense_electronic_level']
        cost_multiplier = 80
        defense_name = "جنگ الکترونیک"
    elif defense_type == 'antifighter':
        current_level = user['defense_antifighter_level']
        cost_multiplier = 120
        defense_name = "ضد جنگنده"
    else:
        await callback.answer("❌ سیستم دفاع نامعتبر!")
        return
    
    upgrade_cost = (current_level + 1) * cost_multiplier
    
    if user['zone_coin'] < upgrade_cost:
        await callback.answer(f"❌ سکه کافی ندارید! نیاز: {upgrade_cost} سکه")
        return
    
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
    
    updated_user = db.get_user(user_id)
    new_total_bonus = min(updated_user['total_defense_bonus'], 0.5) * 100
    
    await callback.message.edit_text(f"""
🛡️ <b>ارتقا موفق!</b>
━━━━━━━━━━━━━━
🏰 سیستم: {defense_name}
📈 لول جدید: {current_level + 1}
💰 هزینه: {upgrade_cost} سکه
━━━━━━━━━━━━━━
🛡️ بانس دفاع کلی: {new_total_bonus:.1f}%
💰 سکه باقی‌مانده: {user['zone_coin'] - upgrade_cost} سکه
━━━━━━━━━━━━━━
✅ سیستم دفاع شما تقویت شد!
⚠️ حداکثر بانس دفاع: 50%
    """)
    await callback.answer(f"✅ {defense_name} ارتقا یافت!")

@dp.message(F.text == "📊 رنکینگ")
async def cmd_ranking(message: Message):
    top_users = db.get_top_users(15)
    
    if not top_users:
        await message.answer("📭 هنوز کاربری در رنکینگ وجود ندارد!")
        return
    
    ranking_text = "🏆 <b>رنکینگ برترین‌های جنگ‌افزار</b>\n━━━━━━━━━━━━━━━━━━\n"
    
    for i, user in enumerate(top_users, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        
        username = user['username'] or user['full_name']
        if len(username) > 15:
            username = username[:15] + "..."
        
        ranking_text += f"{medal} <b>{username}</b>\n"
        ranking_text += f"   💰 {user['zone_coin']:,} سکه | 💎 {user['zone_gem']} جم | ⚡ {user['zone_point']} ZP\n"
        ranking_text += f"   🎯 لول {user['level']} | 👤 {user['user_id']}\n"
        
        if i < len(top_users):
            ranking_text += "━━━━━━━━━━━━━━\n"
    
    ranking_text += f"""
━━━━━━━━━━━━━━━━━━
📈 <b>آمار کلی:</b>
• تعداد کاربران در رنکینگ: {len(top_users)}
• بیشترین سکه: {top_users[0]['zone_coin']:,} سکه
• بالاترین لول: لول {max(u['level'] for u in top_users)}
    """
    
    await message.answer(ranking_text)

@dp.message(F.text == "🆘 پشتیبانی")
async def cmd_support(message: Message):
    support_text = """
🆘 <b>پشتیبانی و راهنما</b>
━━━━━━━━━━━━━━━━━━
📞 <b>ارتباط با مدیریت:</b>
• برای گزارش مشکل: @YourSupportUsername
• برای پیشنهاد: @YourSupportUsername
• برای همکاری: @YourSupportUsername

📖 <b>راهنمای سریع:</b>
• حمله: ریپلای + "حمله با [نام موشک]"
• انتقام: از منوی انتقام یا دکمه در پیام حمله
• ماینر: همیشه قابل برداشت است
• جنگنده: آسیب و دفاع شما را افزایش می‌دهد
• دفاع: از سکه‌های شما محافظت می‌کند

⚠️ <b>قوانین:</b>
1. احترام به دیگر کاربران
2. عدم سوءاستفاده از باگ‌ها
3. گزارش مشکلات به پشتیبانی
4. لطفا اسپم نکنید

💰 <b>دریافت جم:</b>
• فقط از باکس ویژه و افسانه‌ای
• از غنیمت حملات
• هدایای ادمین

🎮 <b>لذت ببرید و پیروز باشید!</b>
    """
    
    await message.answer(support_text)

@dp.callback_query(F.data == "miner_info")
async def cmd_miner_info(callback: CallbackQuery):
    miner_info = """
⛏️ <b>اطلاعات ماینر</b>
━━━━━━━━━━━━━━
📊 <b>ویژگی‌ها:</b>
• تولید دائمی ZP
• همیشه قابل برداشت
• بدون کوئلتایم
• حداکثر 15 سطح

💡 <b>نکات:</b>
• هر ساعت ZP تولید می‌شود
• می‌توانید هر زمان برداشت کنید
• باقی‌مانده ZP ذخیره می‌شود
• ارتقا تولید را افزایش می‌دهد

🎯 <b>اهداف:</b>
• ZP برای ارتقا سیستم‌ها
• خرید آیتم‌های ویژه
• افزایش قدرت کلی
    """
    
    await callback.message.edit_text(miner_info)
    await callback.answer()

@dp.callback_query(F.data == "defense_info")
async def cmd_defense_info(callback: CallbackQuery):
    defense_info = """
🏰 <b>اطلاعات سیستم دفاع</b>
━━━━━━━━━━━━━━
🛡️ <b>دفاع موشکی:</b>
• کاهش خسارت: 5% در هر سطح
• بهترین در برابر: موشک‌های معمولی

📡 <b>جنگ الکترونیک:</b>
• کاهش خسارت: 3% در هر سطح  
• بهترین در برابر: موشک‌های هدایت‌شونده

✈️ <b>ضد جنگنده:</b>
• کاهش خسارت: 7% در هر سطح
• بهترین در برابر: حملات هوایی

━━━━━━━━━━━━━━
⚠️ <b>نکات مهم:</b>
• حداکثر کاهش خسارت: 50%
• هر سیستم در برابر نوع خاصی مؤثر است
• ترکیب سیستم‌ها بهترین نتیجه را می‌دهد
    """
    
    await callback.message.edit_text(defense_info)
    await callback.answer()

@dp.callback_query(F.data == "fighter_info")
async def cmd_fighter_info(callback: CallbackQuery):
    fighter_info = """
✈️ <b>اطلاعات جنگنده</b>
━━━━━━━━━━━━━━
💥 <b>مزایا:</b>
• افزایش آسیب حملات
• افزایش دفاع
• بهبود عملکرد کلی

📊 <b>سطح‌ها:</b>
• 0: پایه (بدون بانس)
• 1: +5% آسیب، +2% دفاع
• 2: +10% آسیب، +4% دفاع
• 3: +15% آسیب، +6% دفاع
• ...
• 10: +50% آسیب، +20% دفاع

━━━━━━━━━━━━━━
🎯 <b>تاثیر:</b>
• در همه حملات تاثیر دارد
• در دفاع هم تاثیر دارد
• ارزش سرمایه‌گذاری دارد
    """
    
    await callback.message.edit_text(fighter_info)
    await callback.answer()

@dp.callback_query(F.data == "box_inventory")
async def cmd_box_inventory(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    
    missiles = db.get_user_missiles(user_id)
    
    inventory_text = f"""
📦 <b>موجودی شما</b>
━━━━━━━━━━━━━━
💰 سکه: {user['zone_coin']}
💎 جم: {user['zone_gem']}
⚡ ZP: {user['zone_point']}
━━━━━━━━━━━━━━
💣 <b>موشک‌ها:</b>
    """
    
    if missiles:
        for missile in missiles:
            inventory_text += f"\n• {missile['missile_name']}: {missile['quantity']} عدد"
    else:
        inventory_text += "\n• هیچ موشکی ندارید!"
    
    inventory_text += f"""
━━━━━━━━━━━━━━
🎯 لول: {user['level']}
⭐ XP: {user['xp']}/{user['level'] * 100}
✈️ جنگنده: لول {user['fighter_level']}
⛏️ ماینر: لول {user['miner_level']}
    """
    
    await callback.message.edit_text(inventory_text)
    await callback.answer()

# === دستورات ادمین ===
@dp.message(F.text == "👑 پنل ادمین")
async def cmd_admin_panel(message: Message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("❌ دسترسی ممنوع! شما ادمین نیستید.")
        return
    
    user = db.get_user(user_id)
    if not user or not user['is_admin']:
        await message.answer("❌ دسترسی ممنوع! شما ادمین نیستید.")
        return
    
    admin_text = f"""
👑 <b>پنل مدیریت ادمین</b>
━━━━━━━━━━━━━━
🆔 آیدی شما: {user_id}
👤 نام: {message.from_user.full_name}
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
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 آمار کامل"), KeyboardButton(text="📢 پیام همگانی")],
            [KeyboardButton(text="🎁 هدیه همگانی"), KeyboardButton(text="➕ سکه")],
            [KeyboardButton(text="💎 جم"), KeyboardButton(text="⚡ ZP")],
            [KeyboardButton(text="📈 تغییر لول"), KeyboardButton(text="🔙 بازگشت")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(admin_text, reply_markup=keyboard)

@dp.message(F.text == "📊 آمار کامل")
async def cmd_admin_stats(message: Message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("❌ دسترسی ممنوع!")
        return
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
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
    
    cursor.execute('SELECT AVG(level) as avg_level FROM users')
    avg_level = cursor.fetchone()['avg_level'] or 0
    
    cursor.execute('''
    SELECT user_id, username, full_name, created_at 
    FROM users 
    ORDER BY created_at DESC 
    LIMIT 5
    ''')
    recent_users = cursor.fetchall()
    
    today = int(time.time()) - 86400
    cursor.execute('SELECT COUNT(*) as today_users FROM users WHERE created_at > ?', (today,))
    today_users = cursor.fetchone()['today_users']
    
    conn.close()
    
    stats_text = f"""
📊 <b>آمار کامل ربات</b>
━━━━━━━━━━━━━━
👥 تعداد کاربران: {total_users}
👤 کاربران امروز: {today_users}
⚔️ تعداد حمله‌ها: {total_attacks}
🎯 میانگین لول: {avg_level:.1f}
━━━━━━━━━━━━━━
💰 کل سکه‌ها: {total_coins:,}
💎 کل جم‌ها: {total_gems:,}  
⚡ کل ZP: {total_zp:,}
━━━━━━━━━━━━━━
📅 <b>آخرین کاربران:</b>
    """
    
    for user in recent_users:
        date = datetime.fromtimestamp(user['created_at']).strftime('%Y/%m/%d %H:%M')
        username = user['username'] or user['full_name']
        stats_text += f"\n• {username} (ID: {user['user_id']}) - {date}"
    
    await message.answer(stats_text)

@dp.message(F.text == "📢 پیام همگانی")
async def cmd_broadcast(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("❌ دسترسی ممنوع!")
        return
    
    await message.answer("📝 لطفا پیام همگانی را ارسال کنید:")
    await state.set_state(UserStates.waiting_for_broadcast)

@dp.message(UserStates.waiting_for_broadcast)
async def process_broadcast(message: Message, state: FSMContext):
    broadcast_text = message.text
    
    users = db.get_all_users()
    
    success = 0
    failed = 0
    
    for user in users:
        try:
            await bot.send_message(
                user['user_id'], 
                f"📢 <b>پیام همگانی از مدیریت</b>\n━━━━━━━━━━━━━━\n{broadcast_text}"
            )
            success += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1
    
    await message.answer(f"""
✅ <b>ارسال پیام همگانی</b>
━━━━━━━━━━━━━━
📤 ارسال شده به: {success} کاربر
❌ ناموفق: {failed} کاربر
📝 متن ارسالی:
{broadcast_text[:100]}...
    """)
    
    await state.clear()

@dp.message(F.text == "🎁 هدیه همگانی")
async def cmd_global_gift(message: Message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("❌ دسترسی ممنوع!")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 500 سکه به همه", callback_data="gift_all_coins_500")],
        [InlineKeyboardButton(text="💎 5 جم به همه", callback_data="gift_all_gems_5")],
        [InlineKeyboardButton(text="⚡ 250 ZP به همه", callback_data="gift_all_zp_250")],
        [InlineKeyboardButton(text="🎁 همه موارد بالا", callback_data="gift_all_everything")],
        [InlineKeyboardButton(text="💣 3 موشک شبح به همه", callback_data="gift_all_missiles")]
    ])
    
    await message.answer("🎁 انتخاب هدیه همگانی:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("gift_all_"))
async def process_global_gift(callback: CallbackQuery):
    gift_type = callback.data.replace("gift_all_", "")
    
    users = db.get_all_users()
    
    if gift_type == 'coins_500':
        for user in users:
            db.update_user_coins(user['user_id'], 500)
        gift_text = "500 سکه"
    elif gift_type == 'gems_5':
        for user in users:
            db.update_user_gems(user['user_id'], 5)
        gift_text = "5 جم"
    elif gift_type == 'zp_250':
        for user in users:
            db.update_user_zp(user['user_id'], 250)
        gift_text = "250 ZP"
    elif gift_type == 'everything':
        for user in users:
            db.update_user_coins(user['user_id'], 500)
            db.update_user_gems(user['user_id'], 5)
            db.update_user_zp(user['user_id'], 250)
        gift_text = "500 سکه + 5 جم + 250 ZP"
    elif gift_type == 'missiles':
        for user in users:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
            INSERT INTO user_missiles (user_id, missile_name, quantity)
            VALUES (?, ?, 3)
            ON CONFLICT(user_id, missile_name) 
            DO UPDATE SET quantity = quantity + 3
            ''', (user['user_id'], 'شبح'))
            conn.commit()
            conn.close()
        gift_text = "3 موشک شبح"
    
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
    
    if not is_admin(user_id):
        await message.answer("❌ دسترسی ممنوع!")
        return
    
    await message.answer("🆔 آیدی کاربر + مقدار سکه (مثال: 123456 1000):")
    await state.set_state(UserStates.waiting_for_gift_amount)

@dp.message(F.text == "💎 جم")
async def cmd_add_gems(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("❌ دسترسی ممنوع!")
        return
    
    await message.answer("🆔 آیدی کاربر + مقدار جم (مثال: 123456 50):")
    await state.set_state(UserStates.waiting_for_gift_amount)

@dp.message(F.text == "⚡ ZP")
async def cmd_add_zp(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("❌ دسترسی ممنوع!")
        return
    
    await message.answer("🆔 آیدی کاربر + مقدار ZP (مثال: 123456 500):")
    await state.set_state(UserStates.waiting_for_gift_amount)

@dp.message(F.text == "📈 تغییر لول")
async def cmd_change_level(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("❌ دسترسی ممنوع!")
        return
    
    await message.answer("🆔 آیدی کاربر + لول جدید (مثال: 123456 10):")
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
        elif "لول" in message.reply_to_message.text:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET level = ? WHERE user_id = ?', (amount, target_id))
            conn.commit()
            conn.close()
            gift_type = "لول"
            new_amount = amount
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

async def main():
    """تابع اصلی"""
    logger.info("🚀 Starting Warzone Bot v3.0...")
    
    async def keep_alive_task():
        while True:
            await keep_alive()
            await asyncio.sleep(300)
    
    asyncio.create_task(keep_alive_task())
    
    logger.info("🤖 Bot is starting to poll...")
    await dp.start_polling(bot)
    logger.info("🛑 Bot polling stopped")

if __name__ == '__main__':
    asyncio.run(main())
