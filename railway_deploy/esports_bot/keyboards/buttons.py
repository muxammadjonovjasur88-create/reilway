from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import GAMES, MLBB_LANES

def channel_check_keyboard(channels):
    buttons = []
    for ch in channels:
        if ch.get("link"):
            buttons.append([InlineKeyboardButton(text=f"➡️ {ch['name']}", url=ch["link"])])
    buttons.append([InlineKeyboardButton(text="✅ A'zo bo'ldim, tekshir!", callback_data="check_subscription")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def games_keyboard(tournaments):
    buttons = [[InlineKeyboardButton(
        text=f"{GAMES.get(t['game'], t['game'])} — {t['title']}",
        callback_data=f"game_{t['id']}"
    )] for t in tournaments]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def tournament_menu_keyboard(tournament_id, is_registered=False):
    buttons = [
        [InlineKeyboardButton(text="📋 Turnir haqida", callback_data=f"t_info_{tournament_id}")],
        [InlineKeyboardButton(text="🏅 ELO Reyting", callback_data=f"elo_board_{tournament_id}")],
    ]
    if not is_registered:
        buttons.append([InlineKeyboardButton(text="✍️ Ro'yxatdan o'tish", callback_data=f"register_{tournament_id}")])
    else:
        buttons.append([InlineKeyboardButton(text="👥 Mening jamoam", callback_data=f"my_team_{tournament_id}")])
    buttons.append([InlineKeyboardButton(text="📊 Jadval", callback_data=f"bracket_{tournament_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def lanes_keyboard():
    buttons = [[InlineKeyboardButton(text=lane, callback_data=f"lane_{lane}")] for lane in MLBB_LANES]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def confirm_keyboard(action, data=""):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"confirm_{action}_{data}"),
        InlineKeyboardButton(text="❌ Bekor", callback_data="cancel"),
    ]])

def match_result_keyboard(match_id, t1_id, t2_id, t1_name, t2_name):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🏆 {t1_name} yutdi", callback_data=f"winner_{match_id}_{t1_id}_{t2_id}")],
        [InlineKeyboardButton(text=f"🏆 {t2_name} yutdi", callback_data=f"winner_{match_id}_{t2_id}_{t1_id}")],
    ])

def admin_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Yangi turnir", callback_data="admin_new_tournament")],
        [InlineKeyboardButton(text="📋 Turnirlar", callback_data="admin_list_tournaments")],
        [InlineKeyboardButton(text="📢 Kanallar/Guruhlar", callback_data="admin_channels")],
        [InlineKeyboardButton(text="⚔️ Matchlar", callback_data="admin_matches")],
        [InlineKeyboardButton(text="🏅 ELO Reyting", callback_data="admin_elo")],
        [InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast")],
    ])

def admin_tournament_keyboard(tid, status):
    buttons = [[InlineKeyboardButton(text="👥 Jamoalar", callback_data=f"admin_t_teams_{tid}")]]
    if status == "draft":
        buttons.append([InlineKeyboardButton(text="🟢 Ro'yxatni ochish", callback_data=f"admin_open_reg_{tid}")])
    elif status == "reg":
        buttons.append([InlineKeyboardButton(text="🎯 Matchlar tuzish", callback_data=f"admin_make_matches_{tid}")])
    elif status == "online":
        buttons.append([InlineKeyboardButton(text="📍 Offline ma'lumotlari", callback_data=f"admin_set_offline_{tid}")])
        buttons.append([InlineKeyboardButton(text="🏁 Offline boshlash", callback_data=f"admin_start_offline_{tid}")])
    buttons.append([InlineKeyboardButton(text="📊 Statistika", callback_data=f"admin_t_stats_{tid}")])
    buttons.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin_list_tournaments")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_games_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=name, callback_data=f"admin_game_{key}")]
        for key, name in GAMES.items()
    ])
