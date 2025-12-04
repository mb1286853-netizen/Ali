"""
هندلر سیستم ترکیب‌سازی
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from keyboards import get_combo_keyboard, get_back_keyboard

def register_combo_handlers(dp):
    """ثبت هندلرهای ترکیب"""
    dp.message.register(combo_panel, F.text == "🔧 سیستم ترکیب")
    dp.callback_query.register(create_combo, F.data == "create_combo")
    dp.callback_query.register(my_combos, F.data == "my_combos")

async def combo_panel(message: Message):
    """منوی سیستم ترکیب"""
    text = """
🔧 **سیستم ترکیب‌سازی**

🎯 **ساخت ترکیب شخصی:**
با موشک‌های مختلف، ترکیب‌های منحصربفرد بساز!

📊 **مزایا:**
• افزایش damage حملات
• ترکیب‌های خاص
• استراتژی‌های متنوع

💡 **نکته:** برای ساخت ترکیب نیاز به موشک‌های مختلف داری!
"""
    await message.answer(text, reply_markup=get_combo_keyboard())

async def create_combo(callback: CallbackQuery):
    """ساخت ترکیب جدید"""
    from main import db
    
    user_id = callback.from_user.id
    missiles = db.get_user_missiles(user_id)
    
    if len(missiles) < 2:
        text = """
❌ **موشک کافی نیست!**

برای ساخت ترکیب نیاز داری:
• حداقل 2 نوع موشک مختلف
• هر موشک حداقل 1 عدد

🏦 به بازار جنگ برو و موشک بخر!
"""
    else:
        text = """
🛠️ **ساخت ترکیب جدید**

🎯 **موشک‌های موجود:**
"""
        for missile in missiles:
            name, quantity = missile
            text += f"\n• {name}: {quantity} عدد"
        
        text += """
        
🔧 **انواع ترکیب:**
1. ترکیب پایه (2 موشک) - 1.3x damage
2. ترکیب پیشرفته (3 موشک) - 1.7x damage
3. ترکیب نخبه (4 موشک) - 2.2x damage

⏳ **به زودی کامل می‌شود...**
"""
    
    await callback.message.edit_text(text, reply_markup=get_back_keyboard())
    await callback.answer()

async def my_combos(callback: CallbackQuery):
    """ترکیب‌های من"""
    text = """
📋 **ترکیب‌های شما**

🔍 در حال حاضر ترکیبی نساخته‌اید!

برای ساخت ترکیب:
1. به بازار جنگ برو
2. موشک‌های مختلف بخر
3. به سیستم ترکیب برگرد
4. ترکیب جدید بساز

🎯 **نیازمندی:** حداقل 2 نوع موشک مختلف
"""
    
    await callback.message.edit_text(text, reply_markup=get_back_keyboard())
    await callback.answer()
