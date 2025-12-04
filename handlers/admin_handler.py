"""
هندلر دستورات ادمین
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
import datetime

def register_admin_handlers(dp):
    """ثبت هندلرهای ادمین"""
    dp.message.register(admin_panel, Command("admin"))
    dp.message.register(gift_command, Command("gift"))
    dp.message.register(bot_status, Command("status"))
    dp.message.register(create_backup, Command("backup"))

async def admin_panel(message: Message):
    """پنل ادمین"""
    from main import DEVELOPER_ID
    
    user_id = message.from_user.id
    
    if str(user_id) != DEVELOPER_ID:
        await message.answer("⛔ دسترسی ممنوع!")
        return
    
    text = f"""
🔐 **پنل مدیریت ادمین**

👨‍💻 توسعه‌دهنده: {DEVELOPER_ID}
🕒 زمان: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📋 **دستورات:**
/gift <آیدی> <نوع> <مقدار> - هدیه دادن
/status - وضعیت ربات
/backup - ایجاد Backup
/stats - آمار کاربران

💎 **توجه:** فقط ادمین می‌تواند جم بدهد!
"""
    await message.answer(text)

async def gift_command(message: Message):
    """هدیه دادن به کاربر"""
    from main import DEVELOPER_ID, db
    
    user_id = message.from_user.id
    
    if str(user_id) != DEVELOPER_ID:
        await message.answer("⛔ فقط توسعه‌دهنده!")
        return
    
    parts = message.text.split()
    if len(parts) != 4:
        await message.answer("""
⚠️ **فرمت صحیح:**
`/gift <آیدی_کاربر> <نوع> <مقدار>`

**انواع:**
• coin - سکه
• gem - جم
• zp - ZP

**مثال:**
`/gift 123456789 coin 1000`
`/gift 123456789 gem 5`
""")
        return
    
    try:
        target_id = int(parts[1])
        resource_type = parts[2].lower()
        amount = int(parts[3])
        
        if amount <= 0:
            await message.answer("❌ مقدار باید مثبت باشد!")
            return
        
        if resource_type == "coin":
            db.update_coins(target_id, amount)
            resource_name = "سکه"
            emoji = "💰"
        elif resource_type == "gem":
            db.update_gems(target_id, amount)
            resource_name = "جم"
            emoji = "💎"
        elif resource_type == "zp":
            db.update_zp(target_id, amount)
            resource_name = "ZP"
            emoji = "🎯"
        else:
            await message.answer("❌ نوع نامعتبر!")
            return
        
        await message.answer(f"""
✅ **هدیه ارسال شد!**

{emoji} **{amount:,} {resource_name}**
👤 **به کاربر:** {target_id}
👨‍💼 **توسط:** {message.from_user.full_name}
""")
        
    except ValueError:
        await message.answer("❌ مقدار نامعتبر!")
    except Exception as e:
        await message.answer(f"❌ خطا: {e}")

async def bot_status(message: Message):
    """وضعیت ربات"""
    from main import DEVELOPER_ID, db
    
    user_id = message.from_user.id
    
    if str(user_id) != DEVELOPER_ID:
        await message.answer("⛔ فقط توسعه‌دهنده!")
        return
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM user_missiles')
    total_missiles = cursor.fetchone()[0]
    
    conn.close()
    
    text = f"""
📊 **وضعیت ربات**

👥 **کاربران:** {total_users}
🚀 **موشک‌ها:** {total_missiles}
🕒 **زمان:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
✅ **وضعیت:** آنلاین

💾 **دیتابیس:** SQLite
🔧 **سیستم:** Railway
"""
    await message.answer(text)

async def create_backup(message: Message):
    """ایجاد Backup"""
    from main import DEVELOPER_ID, db
    
    user_id = message.from_user.id
    
    if str(user_id) != DEVELOPER_ID:
        await message.answer("⛔ فقط توسعه‌دهنده!")
        return
    
    try:
        backup_file = db.create_backup()
        await message.answer(f"""
✅ **Backup ایجاد شد!**

📁 **فایل:** {backup_file}
🕒 **زمان:** {datetime.datetime.now().strftime('%H:%M:%S')}
💾 **وضعیت:** موفق
""")
    except Exception as e:
        await message.answer(f"❌ خطا در Backup: {e}")
