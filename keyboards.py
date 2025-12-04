"""
همه کیبوردهای ربات
"""

from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)

# ==================== REPLY KEYBOARDS ====================
def get_main_keyboard():
    """کیبورد اصلی"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎮 پنل جنگجو")],
            [KeyboardButton(text="🏦 بازار جنگ"), KeyboardButton(text="⛏️ معدن‌چی")],
            [KeyboardButton(text="🔧 سیستم ترکیب"), KeyboardButton(text="⚔️ حمله")],
            [KeyboardButton(text="🎁 جعبه‌ها"), KeyboardButton(text="📞 پشتیبانی")],
            [KeyboardButton(text="📊 آمار من"), KeyboardButton(text="ℹ️ راهنما")]
        ],
        resize_keyboard=True,
        input_field_placeholder="انتخاب کن..."
    )

# ==================== INLINE KEYBOARDS ====================
def get_warrior_keyboard():
    """پنل جنگجو"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💰 کیف پول", callback_data="wallet")],
            [InlineKeyboardButton(text="🚀 زرادخانه", callback_data="arsenal")],
            [InlineKeyboardButton(text="🔧 ترکیب‌ها", callback_data="combos")],
            [InlineKeyboardButton(text="⬅️ بازگشت", callback_data="main_menu")]
        ]
    )

def get_market_keyboard():
    """بازار جنگ"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔥 موشک سریع", callback_data="market_fast")],
            [InlineKeyboardButton(text="💀 موشک آخرالزمانی", callback_data="market_apocalypse")],
            [InlineKeyboardButton(text="⬅️ بازگشت", callback_data="main_menu")]
        ]
    )

def get_miner_keyboard():
    """معدن‌چی"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⛏️ برداشت ZP", callback_data="miner_claim")],
            [InlineKeyboardButton(text="⬆️ ارتقای ماینر", callback_data="miner_upgrade")],
            [InlineKeyboardButton(text="📊 اطلاعات", callback_data="miner_info")],
            [InlineKeyboardButton(text="⬅️ بازگشت", callback_data="main_menu")]
        ]
    )

def get_combo_keyboard():
    """سیستم ترکیب"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛠️ ساخت ترکیب", callback_data="create_combo")],
            [InlineKeyboardButton(text="📋 ترکیب‌های من", callback_data="my_combos")],
            [InlineKeyboardButton(text="⬅️ بازگشت", callback_data="main_menu")]
        ]
    )

def get_attack_keyboard():
    """سیستم حمله"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚡ حمله سریع", callback_data="attack_fast")],
            [InlineKeyboardButton(text="💥 ترکیب شخصی", callback_data="attack_custom")],
            [InlineKeyboardButton(text="⬅️ بازگشت", callback_data="main_menu")]
        ]
    )

def get_support_keyboard():
    """پشتیبانی"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📩 پیام به پشتیبانی", callback_data="send_support")],
            [InlineKeyboardButton(text="📨 پیام‌های من", callback_data="my_tickets")],
            [InlineKeyboardButton(text="⬅️ بازگشت", callback_data="main_menu")]
        ]
    )

def get_back_keyboard():
    """دکمه بازگشت"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ بازگشت", callback_data="main_menu")]
        ]
    )

# ==================== DYNAMIC KEYBOARDS ====================
def get_missile_keyboard(missiles: list, prefix: str = "buy"):
    """کیبورد موشک‌ها"""
    buttons = []
    for missile in missiles:
        name = missile.get("name", missile.get("persian", "Unknown"))
        price = missile.get("price", 0)
        gems = missile.get("gems", 0)
        
        if gems > 0:
            text = f"{name} - {gems} جم"
        else:
            text = f"{name} - {price} سکه"
        
        data = f"{prefix}_{name}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=data)])
    
    buttons.append([InlineKeyboardButton(text="⬅️ بازگشت", callback_data="market")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
