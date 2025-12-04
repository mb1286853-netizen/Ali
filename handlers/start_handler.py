"""
هندلر شروع و منوهای اصلی
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from keyboards import get_main_keyboard, get_warrior_keyboard, get_back_keyboard

router = Router()

def register_start_handlers(dp):
    """ثبت هندلرهای شروع"""
    dp.message.register(warrior_panel, F.text == "🎮 پنل جنگجو")
    dp.message.register(show_help, F.text == "ℹ️ راهنما")
    dp.callback_query.register(back_to_main, F.data == "main_menu")
    dp.callback_query.register(show_wallet, F.data == "wallet")
    dp.callback_query.register(show_arsenal, F.data == "arsenal")

async def handle_start(message: Message, db):
    """پردازش /start"""
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

async def warrior_panel(message: Message):
    """پنل جنگجو"""
    text = """
🎮 **پنل جنگجو**

در این بخش می‌توانی:
• کیف پول خود را ببینی
• زرادخانه موشک‌ها را مدیریت کنی
• ترکیب‌های شخصی بسازی
"""
    await message.answer(text, reply_markup=get_warrior_keyboard())

async def show_help(message: Message):
    """راهنما"""
    text = """
ℹ️ **راهنمای ربات**

🎮 **منوها:**
• پنل جنگجو: وضعیت شما
• بازار جنگ: خرید موشک
• معدن‌چی: کسب درآمد
• سیستم ترکیب: ساخت ترکیب شخصی
• حمله: حمله به دیگران

📞 **پشتیبانی:** از منوی اصلی
"""
    await message.answer(text, reply_markup=get_back_keyboard())

async def back_to_main(callback: CallbackQuery):
    """بازگشت به منوی اصلی"""
    await callback.message.delete()
    await callback.message.answer("🏠 منوی اصلی:", reply_markup=get_main_keyboard())
    await callback.answer()

async def show_wallet(callback: CallbackQuery):
    """نمایش کیف پول"""
    from main import db
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
