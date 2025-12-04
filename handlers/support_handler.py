"""
هندلر سیستم پشتیبانی
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from keyboards import get_support_keyboard, get_back_keyboard

def register_support_handlers(dp):
    """ثبت هندلرهای پشتیبانی"""
    dp.message.register(support_panel, F.text == "📞 پشتیبانی")
    dp.callback_query.register(send_support, F.data == "send_support")
    dp.callback_query.register(my_tickets, F.data == "my_tickets")

async def support_panel(message: Message):
    """منوی پشتیبانی"""
    from main import DEVELOPER_ID
    
    text = f"""
📞 **سیستم پشتیبانی**

🤝 برای ارتباط با ادمین:
• فقط موارد مهم و باگ‌ها
• عدم ارسال اسپم
• احترام متقابل

⏰ **زمان پاسخگویی:**
• معمولاً 24-48 ساعت

👨‍💻 **توسعه‌دهنده:** @{DEVELOPER_ID}
"""
    await message.answer(text, reply_markup=get_support_keyboard())

async def send_support(callback: CallbackQuery):
    """ارسال پیام به پشتیبانی"""
    text = """
📩 **ارسال پیام به پشتیبانی**

✍️ **لطفاً پیام خود را بنویسید:**
• مشکل یا سوال خود را کامل توضیح دهید
• در صورت باگ، تصویر ارسال کنید

⚠️ **توجه:**
• فقط پیام‌های مهم
• اسپم = مسدود شدن
• پاسخ ممکن است زمان‌بر باشد

💬 **پیام خود را همین حالا بنویس...**
"""
    
    await callback.message.edit_text(text, reply_markup=get_back_keyboard())
    await callback.answer("پیام خود را بنویسید...")

async def my_tickets(callback: CallbackQuery):
    """پیام‌های من"""
    text = """
📨 **پیام‌های پشتیبانی**

📭 **هیچ پیامی نداری!**

برای ارسال پیام جدید، دکمه زیر را بزن:
"""
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📩 پیام جدید", callback_data="send_support")],
            [InlineKeyboardButton(text="⬅️ بازگشت", callback_data="main_menu")]
        ]
    )
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()
