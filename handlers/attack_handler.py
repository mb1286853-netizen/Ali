"""
هندلر سیستم حمله
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from keyboards import get_attack_keyboard, get_back_keyboard
import random

def register_attack_handlers(dp):
    """ثبت هندلرهای حمله"""
    dp.message.register(attack_panel, F.text == "⚔️ حمله")
    dp.callback_query.register(attack_fast, F.data == "attack_fast")
    dp.callback_query.register(attack_custom, F.data == "attack_custom")

async def attack_panel(message: Message):
    """منوی حمله"""
    text = """
⚔️ **سیستم حمله**

🎯 **انواع حمله:**

⚡ **حمله سریع:** با یک موشک
🔧 **ترکیب شخصی:** با ترکیب ساخته‌شده

📝 **نحوه حمله:**
1. روی پیام کاربر ریپلای کن
2. دکمه حمله را بزن
3. نوع حمله را انتخاب کن

⚠️ **توجه:** حمله نیاز به موشک دارد!
"""
    await message.answer(text, reply_markup=get_attack_keyboard())

async def attack_fast(callback: CallbackQuery):
    """حمله سریع"""
    from main import db
    
    if callback.message.reply_to_message is None:
        await callback.answer("❌ روی پیام کاربر ریپلای کن!", show_alert=True)
        return
    
    attacker_id = callback.from_user.id
    target_id = callback.message.reply_to_message.from_user.id
    
    if attacker_id == target_id:
        await callback.answer("❌ نمی‌توانی به خودت حمله کنی!", show_alert=True)
        return
    
    # چک کردن کاربران
    attacker = db.get_user(attacker_id)
    target = db.get_user(target_id)
    
    if not attacker or not target:
        await callback.answer("❌ کاربر یافت نشد!", show_alert=True)
        return
    
    # چک کردن موشک
    missiles = db.get_user_missiles(attacker_id)
    if not missiles:
        await callback.answer("❌ موشک ندارید!", show_alert=True)
        return
    
    # محاسبه damage
    base_damage = random.randint(50, 150)
    attacker_level = attacker[6]
    target_level = target[6]
    
    # اعمال bonus سطح
    level_bonus = 1 + (attacker_level - target_level) * 0.1
    final_damage = int(base_damage * level_bonus)
    
    # اعمال damage
    new_target_zp = max(0, target[5] - final_damage)
    db.update_zp(target_id, -final_damage)
    
    # کم کردن یک موشک
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE user_missiles 
        SET quantity = quantity - 1 
        WHERE user_id = ? AND quantity > 0 
        LIMIT 1
    ''', (attacker_id,))
    conn.commit()
    conn.close()
    
    text = f"""
⚔️ **حمله انجام شد!**

🎯 **هدف:** {callback.message.reply_to_message.from_user.full_name}
⚡ **Damage:** {final_damage}
📉 **ZP از دست رفته:** {final_damage}
🎯 **ZP جدید هدف:** {new_target_zp}

✨ حمله موفق بود!
"""
    
    await callback.message.edit_text(text, reply_markup=get_back_keyboard())
    await callback.answer("✅ حمله شد!")

async def attack_custom(callback: CallbackQuery):
    """حمله با ترکیب شخصی"""
    from main import db
    
    text = """
🔧 **حمله با ترکیب شخصی**

این ویژگی به زودی اضافه می‌شود!

📌 فعلاً از حمله سریع استفاده کن.
"""
    
    await callback.message.edit_text(text, reply_markup=get_back_keyboard())
    await callback.answer("⏳ به زودی...")
