"""
هندلر معدن‌چی
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from keyboards import get_miner_keyboard, get_back_keyboard
import time

def register_miner_handlers(dp):
    """ثبت هندلرهای معدن‌چی"""
    dp.message.register(miner_panel, F.text == "⛏️ معدن‌چی")
    dp.callback_query.register(claim_miner, F.data == "miner_claim")
    dp.callback_query.register(upgrade_miner, F.data == "miner_upgrade")
    dp.callback_query.register(miner_info, F.data == "miner_info")

async def miner_panel(message: Message):
    """منوی معدن‌چی"""
    from main import db
    
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

💰 **ارتقا:** {miner_level * 200} سکه
📈 **سطح بعدی:** {(miner_level + 1) * 100} ZP/ساعت
"""
    else:
        text = "⚠️ ابتدا با /start ثبت‌نام کن!"
    
    await message.answer(text, reply_markup=get_miner_keyboard())

async def claim_miner(callback: CallbackQuery):
    """برداشت از ماینر"""
    from main import db
    
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await callback.answer("⚠️ ابتدا ثبت‌نام کن!", show_alert=True)
        return
    
    current_time = int(time.time())
    last_claim = user[11]
    miner_level = user[10]
    
    # چک کردن زمان
    if last_claim > 0 and (current_time - last_claim) < 3600:
        remaining = 3600 - (current_time - last_claim)
        minutes = remaining // 60
        seconds = remaining % 60
        await callback.answer(f"⏳ {minutes} دقیقه و {seconds} ثانیه دیگر", show_alert=True)
        return
    
    # محاسبه درآمد
    income = miner_level * 100
    
    # بروزرسانی دیتابیس
    db.update_zp(user_id, income)
    
    # بروزرسانی زمان آخرین برداشت
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET last_miner_claim = ? WHERE user_id = ?', 
                  (current_time, user_id))
    conn.commit()
    conn.close()
    
    # دریافت اطلاعات جدید
    user = db.get_user(user_id)
    
    text = f"""
⛏️ **برداشت موفق!**

✅ **درآمد:** +{income} ZP
📊 **کل ZP:** {user[5]:,}
💰 **ماینر:** سطح {miner_level}
⏰ **برداشت بعدی:** 1 ساعت دیگر
"""
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬆️ ارتقا", callback_data="miner_upgrade")],
            [InlineKeyboardButton(text="📊 اطلاعات", callback_data="miner_info")],
            [InlineKeyboardButton(text="⬅️ بازگشت", callback_data="main_menu")]
        ]
    )
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer("✅ برداشت شد!")

async def upgrade_miner(callback: CallbackQuery):
    """ارتقای ماینر"""
    from main import db
    
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await callback.answer("⚠️ ابتدا ثبت‌نام کن!", show_alert=True)
        return
    
    miner_level = user[10]
    upgrade_cost = miner_level * 200
    
    if user[3] < upgrade_cost:
        await callback.answer(f"❌ سکه کافی نیست! نیاز: {upgrade_cost}", show_alert=True)
        return
    
    # ارتقای ماینر
    db.update_coins(user_id, -upgrade_cost)
    
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

✅ ماینر به سطح {user[10]} ارتقا یافت!
💰 هزینه: {upgrade_cost} سکه
💎 باقی‌مانده: {user[3]:,} سکه
📈 درآمد جدید: {user[10] * 100} ZP/ساعت
"""
    
    await callback.message.edit_text(text, reply_markup=get_back_keyboard())
    await callback.answer("✅ ماینر ارتقا یافت!")

async def miner_info(callback: CallbackQuery):
    """اطلاعات ماینر"""
    from main import db
    
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await callback.answer("⚠️ ابتدا ثبت‌نام کن!", show_alert=True)
        return
    
    miner_level = user[10]
    last_claim = user[11]
    current_time = int(time.time())
    
    # محاسبه زمان باقی‌مانده
    if last_claim == 0:
        time_status = "✅ آماده برداشت"
    elif (current_time - last_claim) < 3600:
        remaining = 3600 - (current_time - last_claim)
        minutes = remaining // 60
        seconds = remaining % 60
        time_status = f"⏳ {minutes}:{seconds:02d} دیگر"
    else:
        time_status = "✅ آماده برداشت"
    
    text = f"""
⛏️ **اطلاعات ماینر**

📊 **وضعیت فعلی:**
• سطح: {miner_level}
• درآمد ساعتی: {miner_level * 100} ZP
• وضعیت برداشت: {time_status}

💰 **هزینه ارتقا:** {miner_level * 200} سکه
📈 **درآمد بعدی:** {(miner_level + 1) * 100} ZP/ساعت
"""
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⛏️ برداشت", callback_data="miner_claim")],
            [InlineKeyboardButton(text="⬆️ ارتقا", callback_data="miner_upgrade")],
            [InlineKeyboardButton(text="⬅️ بازگشت", callback_data="main_menu")]
        ]
    )
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()
