import random, asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, InputMediaPhoto
from aiogram.filters import Command
from config import ADMIN_IDS, TOURNAMENT_FORMATS, DRAW_FRAMES
import database as db

router = Router()
def is_admin(uid): return uid in ADMIN_IDS

def adm_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Yangi turnir",      callback_data="adm_new_t"),
         InlineKeyboardButton(text="📋 Turnirlar",         callback_data="adm_list_t")],
        [InlineKeyboardButton(text="📢 Kanallar",          callback_data="adm_channels"),
         InlineKeyboardButton(text="⚔️ Matchlar",          callback_data="adm_matches_btn")],
        [InlineKeyboardButton(text="📸 Screenshots",       callback_data="adm_screenshots"),
         InlineKeyboardButton(text="📨 Xabarlar",          callback_data="adm_tickets")],
        [InlineKeyboardButton(text="📩 Liderlarga xabar",  callback_data="adm_dm_leaders"),
         InlineKeyboardButton(text="📊 Statistika",        callback_data="adm_stats")],
        [InlineKeyboardButton(text="📢 Broadcast",         callback_data="adm_broadcast")],
    ])

@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id): await message.answer("❌ Admin huquqi yo'q."); return
    # Ochiq ticketlar soni
    tickets = db.get_open_tickets()
    text = "🛠 <b>Admin Panel</b>"
    if tickets: text += f"\n\n📨 <b>{len(tickets)} ta yangi xabar!</b>"
    await message.answer(text, reply_markup=adm_kb(), parse_mode="HTML")

@router.callback_query(F.data == "adm_back")
async def adm_back(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    tickets = db.get_open_tickets()
    text = "🛠 <b>Admin Panel</b>"
    if tickets: text += f"\n\n📨 <b>{len(tickets)} ta yangi xabar!</b>"
    await call.message.edit_text(text, reply_markup=adm_kb(), parse_mode="HTML")

# ── KANALLAR ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_channels")
async def adm_channels(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    chs = db.get_channels()
    text = "📢 <b>Kanallar</b>\n\n" + ("".join(f"• <b>{c['name']}</b> — <code>{c['id']}</code>\n" for c in chs) or "Yo'q\n")
    btns = [[InlineKeyboardButton(text=f"🗑 {c['name']}", callback_data=f"del_ch_{c['id']}")] for c in chs]
    btns += [[InlineKeyboardButton(text="➕ Qo'shish", callback_data="add_ch")],
             [InlineKeyboardButton(text="◀️ Orqaga", callback_data="adm_back")]]
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")

@router.callback_query(F.data == "add_ch")
async def add_ch(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    db.set_state(call.from_user.id,"admin_add_channel",{})
    await call.message.answer("Format: <code>-1001234567890 Kanal nomi</code>", parse_mode="HTML")

@router.callback_query(F.data.startswith("del_ch_"))
async def del_ch(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    db.remove_channel(int(call.data.replace("del_ch_",""))); await call.answer("✅ O'chirildi!")
    await adm_channels(call)

# ── E'LON (RASM/GIF BILAN) ────────────────────────────────────────────

@router.callback_query(F.data == "adm_broadcast")
async def adm_broadcast(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    db.set_state(call.from_user.id,"admin_broadcast_media",{})
    await call.message.answer(
        "📢 <b>Broadcast xabar</b>\n\n"
        "Xabar yuboring. Rasm, GIF yoki video ham qo'shishingiz mumkin:\n\n"
        "• Faqat matn yuboring\n"
        "• Yoki rasm/GIF ga izoh yozing (caption)\n"
        "• /skip — oldingi media bilan",
        parse_mode="HTML"
    )

# ── TURNIR YARATISH ───────────────────────────────────────────────────

@router.callback_query(F.data == "adm_new_t")
async def new_tournament(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    btns = [[InlineKeyboardButton(text=v, callback_data=f"fmt_{k}")] for k,v in TOURNAMENT_FORMATS.items()]
    await call.message.edit_text("🎮 <b>Format tanlang:</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")

@router.callback_query(F.data.startswith("fmt_"))
async def select_fmt(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    fmt = call.data.replace("fmt_","")
    db.set_state(call.from_user.id,"admin_title",{"format":fmt})
    await call.message.edit_text(f"✅ <b>{TOURNAMENT_FORMATS[fmt]}</b>\n\n🏆 Turnir nomini yuboring:", parse_mode="HTML")

@router.callback_query(F.data == "confirm_create_t")
async def confirm_create(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    _, data = db.get_state(call.from_user.id)
    tid = db.create_tournament(data, call.from_user.id)
    db.clear_state(call.from_user.id)
    await call.message.edit_text(f"✅ <b>Turnir #{tid} yaratildi!</b>", reply_markup=_t_kb(tid,"draft"), parse_mode="HTML")

@router.callback_query(F.data == "cancel_admin")
async def cancel_admin(call: CallbackQuery):
    db.clear_state(call.from_user.id)
    await call.message.edit_text("❌ Bekor qilindi.", reply_markup=adm_kb())

# ── TURNIRLAR ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_list_t")
async def list_t(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    ts = db.get_all_tournaments()
    if not ts: await call.answer("Hali turnirlar yo'q!", show_alert=True); return
    icons = {"draft":"📝","reg":"✍️","checkin":"✅","online":"⚔️","offline":"🏟️","finished":"🏁"}
    btns = [[InlineKeyboardButton(text=f"{icons.get(t['status'],'•')} {t['title']} (#{t['id']})", callback_data=f"td_{t['id']}")] for t in ts]
    btns.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="adm_back")])
    await call.message.edit_text("📋 <b>Barcha turnirlar:</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")

@router.callback_query(F.data.startswith("td_"))
async def t_detail(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    try: tid = int(call.data.split("_")[1])
    except: return
    t = db.get_tournament(tid)
    teams = db.get_teams_by_tournament(tid)
    checked = len([tm for tm in teams if tm.get("checked_in")])
    text = (
        f"🏆 <b>{t['title']}</b> (#{t['id']})\n"
        f"📌 {t['status']} | 🎮 {TOURNAMENT_FORMATS.get(t['format'],t['format'])}\n"
        f"👥 Jamoalar: {len(teams)}/{t['max_teams']} | Check-in: {checked}\n"
        f"💰 {t.get('prize_pool') or '—'}\n"
    )
    await call.message.edit_text(text, reply_markup=_t_kb(tid,t["status"]), parse_mode="HTML")

def _t_kb(tid, status):
    b = [
        [InlineKeyboardButton(text="👥 Jamoalar",     callback_data=f"t_teams_{tid}"),
         InlineKeyboardButton(text="📊 Statistika",   callback_data=f"t_stats_{tid}")],
        [InlineKeyboardButton(text="📄 PDF Jamoalar", callback_data=f"pdf_teams_{tid}"),
         InlineKeyboardButton(text="📄 PDF Matchlar", callback_data=f"pdf_matches_{tid}")],
    ]
    if status=="draft":
        b.append([InlineKeyboardButton(text="🟢 Ro'yxat ochish", callback_data=f"open_reg_{tid}")])
        b.append([InlineKeyboardButton(text="🖼 Banner qo'shish", callback_data=f"set_banner_{tid}")])
    elif status in ("reg","checkin"):
        b.append([InlineKeyboardButton(text="✅ Check-in ochish",  callback_data=f"open_checkin_{tid}")])
        b.append([InlineKeyboardButton(text="🎲 Qura tashlash",    callback_data=f"draw_matches_{tid}")])
    elif status=="online":
        b.append([InlineKeyboardButton(text="📍 Offline ma'lumot", callback_data=f"set_offline_{tid}")])
        b.append([InlineKeyboardButton(text="🏁 Offline boshlash", callback_data=f"start_offline_{tid}")])
    b.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="adm_list_t")])
    return InlineKeyboardMarkup(inline_keyboard=b)

@router.callback_query(F.data.startswith("open_reg_"))
async def open_reg(call: CallbackQuery, bot: Bot):
    if not is_admin(call.from_user.id): return
    tid = int(call.data.replace("open_reg_",""))
    db.update_tournament(tid, status="reg")
    t = db.get_tournament(tid)
    bot_info = await bot.get_me()
    await call.answer("✅ Ro'yxat ochildi!")
    # Banner bormi?
    announce_text = (
        f"📢 <b>YANGI MLBB TURNIRI!</b>\n\n"
        f"🏆 {t['title']}\n"
        f"🎮 {TOURNAMENT_FORMATS.get(t['format'])}\n"
        f"💰 {t.get('prize_pool') or '—'}\n"
        + (f"🥇 {t['prize_distribution']}\n" if t.get("prize_distribution") else "")
        + f"\n✍️ Ro'yxat: @{bot_info.username}"
    )
    if t.get("banner_file_id"):
        await call.message.answer_photo(t["banner_file_id"], caption=announce_text, parse_mode="HTML")
    else:
        await call.message.answer(announce_text, parse_mode="HTML")
    await call.message.edit_reply_markup(reply_markup=_t_kb(tid,"reg"))

@router.callback_query(F.data.startswith("set_banner_"))
async def set_banner(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    tid = int(call.data.replace("set_banner_",""))
    db.set_state(call.from_user.id,"admin_banner",{"tournament_id":tid})
    await call.message.answer("🖼 Turnir bannerini (rasm) yuboring:")

@router.callback_query(F.data.startswith("open_checkin_"))
async def open_checkin(call: CallbackQuery, bot: Bot):
    if not is_admin(call.from_user.id): return
    tid = int(call.data.replace("open_checkin_",""))
    db.update_tournament(tid, status="checkin")
    t = db.get_tournament(tid)
    teams = db.get_teams_by_tournament(tid)
    notified = set()
    for tm in [t2 for t2 in teams if t2["status"]=="complete"]:
        for p in db.get_team_players(tm["id"]):
            if p["user_id"] not in notified:
                try:
                    await bot.send_message(p["user_id"],
                        f"⏰ <b>CHECK-IN BOSHLANDI!</b>\n\n🏆 {t['title']}\n\n"
                        f"/start → turnir → ✅ Check-in\n⚠️ 30 daqiqa ichida qilmasangiz — disqualifikatsiya!",
                        parse_mode="HTML"); notified.add(p["user_id"])
                except: pass
    await call.answer(f"✅ {len(notified)} o'yinchiga xabar!")
    await call.message.edit_reply_markup(reply_markup=_t_kb(tid,"checkin"))

# ── QURA TASHLASH (RANDOM DRAW ANIMATION) ────────────────────────────

@router.callback_query(F.data.startswith("draw_matches_"))
async def draw_matches(call: CallbackQuery, bot: Bot):
    if not is_admin(call.from_user.id): return
    tid = int(call.data.replace("draw_matches_",""))
    t = db.get_tournament(tid)
    teams = db.get_teams_by_tournament(tid)
    ready = [tm for tm in teams if tm.get("checked_in") or tm["status"]=="complete"]
    if len(ready) < 2:
        await call.answer("Kamida 2 ta tayyor jamoa kerak!", show_alert=True); return

    # Animatsiya boshlash
    msg = await call.message.answer("🎲 <b>Qura tashlash boshlanmoqda...</b>", parse_mode="HTML")

    random.shuffle(ready)

    # Animatsiya frames
    for frame in DRAW_FRAMES:
        await asyncio.sleep(0.8)
        try:
            random.shuffle(ready)
            preview = " 🆚 ".join([ready[i]["team_name"] for i in range(min(4, len(ready)))])
            await msg.edit_text(f"{frame}\n\n<code>{preview}...</code>", parse_mode="HTML")
        except: pass

    await asyncio.sleep(1)

    # Juftlashtirish
    random.shuffle(ready)
    pairs = []
    solo = None
    for i in range(0, len(ready)-1, 2):
        pairs.append((ready[i], ready[i+1]))
    if len(ready) % 2 == 1:
        solo = ready[-1]

    round_names = {1:"1-bosqich", 2:"Chorak Final", 3:"Yarim Final", 4:"Final"}
    count = 0
    result_text = "🎯 <b>QURA NATIJALARI</b>\n\n"
    result_text += "━━━━━━━━━━━━━━━━━━━━\n"

    for i, (t1, t2) in enumerate(pairs, 1):
        mid = db.create_match(tid, 1, t1["id"], t2["id"], round_names.get(1,"1-bosqich"))
        result_text += f"⚔️ <b>Match #{mid}</b>\n"
        result_text += f"  🔴 {t1['team_name']}\n"
        result_text += f"  🔵 {t2['team_name']}\n"
        result_text += f"━━━━━━━━━━━━━━━━━━━━\n"
        count += 1

    if solo:
        result_text += f"\n⚡ <b>{solo['team_name']}</b> — Bye (keyingi raundga o'tdi)\n"

    db.update_tournament(tid, status="online")

    await msg.edit_text(
        f"🎊 <b>QURA TASHLASH TUGADI!</b>\n\n"
        f"{result_text}\n"
        f"📊 Jami: {count} ta match\n\n"
        f"Lobby berish: <code>/lobby MATCH_ID LOBBY_ID PAROL</code>",
        parse_mode="HTML"
    )

    # Barcha o'yinchilarga match juftligini yuborish
    for t1, t2 in pairs:
        for team in [t1, t2]:
            opponent = t2 if team["id"]==t1["id"] else t1
            for p in db.get_team_players(team["id"]):
                try:
                    await bot.send_message(p["user_id"],
                        f"🎯 <b>Raqibingiz aniqlandi!</b>\n\n"
                        f"⚔️ <b>{team['team_name']}</b>\n"
                        f"     vs\n"
                        f"⚔️ <b>{opponent['team_name']}</b>\n\n"
                        f"Lobby ID kelishini kuting! ⏳",
                        parse_mode="HTML")
                except: pass

@router.callback_query(F.data.startswith("t_teams_"))
async def t_teams(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    tid = int(call.data.replace("t_teams_",""))
    teams = db.get_teams_by_tournament(tid)
    t = db.get_tournament(tid)
    if not teams: await call.answer("Hali jamoalar yo'q!", show_alert=True); return
    text = f"👥 <b>Jamoalar ({len(teams)}/{t['max_teams']})</b>\n\n"
    icons = {"complete":"✅","pending":"⏳","eliminated":"❌","winner":"🏆","checked_in":"✔️"}
    for i,tm in enumerate(teams,1):
        players = db.get_team_players(tm["id"])
        ci = "✅" if tm.get("checked_in") else "❌"
        text += (f"{i}. {icons.get(tm['status'],'•')} <b>{tm['team_name']}</b>\n"
                 f"   🏫 {tm.get('school','—')} | Check:{ci} | W:{tm['wins']} L:{tm['losses']}\n"
                 f"   👑 @{tm['leader_username']} | {len(players)}/{t.get('team_size',5)}\n\n")
    await call.message.answer(text, parse_mode="HTML")

@router.callback_query(F.data.startswith("t_stats_"))
async def t_stats(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    tid = int(call.data.replace("t_stats_",""))
    teams = db.get_teams_by_tournament(tid)
    matches = db.get_finished_matches(tid)
    text = f"📊 <b>Statistika</b> | Matchlar: {len(matches)}\n\n"
    text += f"{'#':<3}{'Jamoa':<14}{'W':<4}{'L':<4}{'Pts':<5}Holat\n"+"─"*38+"\n"
    for i,tm in enumerate(teams,1):
        st = {"complete":"✅","pending":"⏳","eliminated":"❌","winner":"🏆","checked_in":"✔️"}.get(tm["status"],"•")
        text += f"{i:<3}{tm['team_name'][:12]:<14}{tm['wins']:<4}{tm['losses']:<4}{tm['points']:<5}{st}\n"
    await call.message.answer(f"<pre>{text}</pre>", parse_mode="HTML")

# ── PDF ───────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("pdf_teams_"))
async def pdf_teams(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    tid = int(call.data.replace("pdf_teams_",""))
    await call.answer("📄 PDF tayyorlanmoqda...")
    t = db.get_tournament(tid)
    from utils.pdf_generator import generate_teams_pdf
    import os
    path = generate_teams_pdf(tid)
    doc = FSInputFile(path, filename=f"jamoalar_{t['title']}.pdf")
    await call.message.answer_document(doc, caption=f"📄 <b>{t['title']}</b> — Jamoalar", parse_mode="HTML")
    os.unlink(path)

@router.callback_query(F.data.startswith("pdf_matches_"))
async def pdf_matches(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    tid = int(call.data.replace("pdf_matches_",""))
    await call.answer("📄 PDF tayyorlanmoqda...")
    t = db.get_tournament(tid)
    from utils.pdf_generator import generate_matches_pdf
    import os
    path = generate_matches_pdf(tid)
    doc = FSInputFile(path, filename=f"matchlar_{t['title']}.pdf")
    await call.message.answer_document(doc, caption=f"📄 <b>{t['title']}</b> — Matchlar", parse_mode="HTML")
    os.unlink(path)

# ── OFFLINE ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("set_offline_"))
async def set_offline(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    tid = int(call.data.replace("set_offline_",""))
    db.set_state(call.from_user.id,"admin_offline_location",{"tournament_id":tid})
    await call.message.answer("📍 Offline manzilni kiriting:")

@router.callback_query(F.data.startswith("start_offline_"))
async def start_offline(call: CallbackQuery, bot: Bot):
    if not is_admin(call.from_user.id): return
    tid = int(call.data.replace("start_offline_",""))
    t = db.get_tournament(tid)
    db.update_tournament(tid, status="offline")
    msg = (f"🏟️ <b>OFFLINE BOSQICH!</b>\n\n🏆 {t['title']}\n"
           + (f"📍 {t['offline_location']}\n" if t.get("offline_location") else "")
           + (f"📅 {t['offline_date']}\n" if t.get("offline_date") else "")
           + "\nHammani kutamiz! 💪")
    notified = set()
    for tm in db.get_teams_by_tournament(tid):
        if tm["status"] not in ("eliminated",):
            for p in db.get_team_players(tm["id"]):
                if p["user_id"] not in notified:
                    try: await bot.send_message(p["user_id"],msg,parse_mode="HTML"); notified.add(p["user_id"])
                    except: pass
    await call.answer(f"✅ {len(notified)} o'yinchiga xabar!")

# ── MATCHLAR ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_matches_btn")
async def adm_matches_btn(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    await call.message.answer(
        "⚔️ <b>Match boshqaruvi</b>\n\n"
        "📋 Ko'rish: <code>/match</code>\n"
        "🔑 Lobby: <code>/lobby MATCH_ID LOBBY_ID [PAROL]</code>\n"
        "✅ Natija: Match ko'rib, g'olibni tanlang",
        parse_mode="HTML"
    )

@router.message(Command("lobby"))
async def set_lobby(message: Message, bot: Bot):
    if not is_admin(message.from_user.id): return
    parts = message.text.split()
    if len(parts)<3: await message.answer("Format: <code>/lobby MATCH_ID LOBBY_ID [PAROL]</code>", parse_mode="HTML"); return
    mid, lid = int(parts[1]), parts[2]
    pwd = parts[3] if len(parts)>3 else ""
    db.set_lobby(mid, lid, pwd)
    m = db.get_match(mid)
    t1=db.get_team(m["team1_id"]); t2=db.get_team(m["team2_id"])

    lobby_msg = (
        f"🔑 <b>LOBBY TAYYOR!</b>\n\n"
        f"⚔️ <b>{t1['team_name']}</b>\n"
        f"         VS\n"
        f"⚔️ <b>{t2['team_name']}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🎮 Lobby ID: <code>{lid}</code>\n"
        + (f"🔐 Parol: <code>{pwd}</code>\n" if pwd else "")
        + f"━━━━━━━━━━━━━━━━━━\n"
        + f"O'yinga kiring va boshlang! 💪🏆"
    )

    # Faqat liderlarga yuborish
    notified = set()
    for team in [t1, t2]:
        leader_id = team["leader_id"]
        if leader_id not in notified:
            try:
                await bot.send_message(leader_id, lobby_msg, parse_mode="HTML")
                notified.add(leader_id)
            except: pass
        # Guruh chatiga ham yuborish
        if team.get("chat_id"):
            try: await bot.send_message(team["chat_id"], lobby_msg, parse_mode="HTML")
            except: pass

    await message.answer(
        f"✅ <b>Match #{mid}</b>\n"
        f"⚔️ {t1['team_name']} vs {t2['team_name']}\n"
        f"🔑 Lobby: <code>{lid}</code>\n"
        f"📨 {len(notified)} ta liderga yuborildi",
        parse_mode="HTML"
    )

@router.message(Command("match"))
async def view_matches(message: Message):
    if not is_admin(message.from_user.id): return
    ts = db.get_active_tournaments()
    if not ts: await message.answer("Faol turnir yo'q."); return
    matches = db.get_pending_matches(ts[0]["id"])
    if not matches: await message.answer("✅ Kutilayotgan match yo'q."); return
    for m in matches:
        t1=db.get_team(m["team1_id"]); t2=db.get_team(m["team2_id"])
        lobby = f"<code>{m['lobby_id']}</code>" if m.get("lobby_id") else "❌ Berilmagan"
        await message.answer(
            f"⚔️ <b>Match #{m['id']}</b> | {m.get('round_name','')}\n"
            f"🔴 <b>{t1['team_name']}</b> [{t1.get('school','—')}]\n"
            f"     vs\n"
            f"🔵 <b>{t2['team_name']}</b> [{t2.get('school','—')}]\n"
            f"🔑 Lobby: {lobby}\n\n"
            f"G'olibni tanlang:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"🏆 {t1['team_name']} — WIN",   callback_data=f"win_{m['id']}_{t1['id']}_{t2['id']}_win")],
                [InlineKeyboardButton(text=f"🏆 {t2['team_name']} — WIN",   callback_data=f"win_{m['id']}_{t2['id']}_{t1['id']}_win")],
                [InlineKeyboardButton(text=f"🔴 {t1['team_name']} — DEF",   callback_data=f"win_{m['id']}_{t2['id']}_{t1['id']}_def")],
                [InlineKeyboardButton(text=f"🔵 {t2['team_name']} — DEF",   callback_data=f"win_{m['id']}_{t1['id']}_{t2['id']}_def")],
            ]),
            parse_mode="HTML"
        )

@router.callback_query(F.data.startswith("win_"))
async def set_winner(call: CallbackQuery, bot: Bot):
    if not is_admin(call.from_user.id): return
    parts = call.data.split("_")
    # win_MID_WID_LID_TYPE
    mid, wid, lid, rtype = int(parts[1]), int(parts[2]), int(parts[3]), parts[4]
    db.submit_result(mid, wid, lid, result_type=rtype)
    winner=db.get_team(wid); loser=db.get_team(lid)
    result_icon = "🏆 WIN" if rtype=="win" else "🚫 DEF (Texnik mag'lubiyat)"

    # MVP keyboard
    mvp_btns = [[InlineKeyboardButton(
        text=f"⭐ {p.get('mlbb_nick') or p['username']} ({p['lane']})",
        callback_data=f"mvp_{mid}_{p['user_id']}"
    )] for p in db.get_team_players(wid)]
    mvp_btns.append([InlineKeyboardButton(text="⏭ O'tkazib yuborish", callback_data=f"skip_mvp_{mid}")])

    await call.message.edit_text(
        f"✅ <b>Natija saqlandi!</b>\n\n"
        f"🏆 <b>{winner['team_name']}</b> — {result_icon}\n"
        f"❌ <b>{loser['team_name']}</b>\n\n"
        f"⭐ MVP tanlang (g'olib jamoasidan):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=mvp_btns),
        parse_mode="HTML"
    )

    win_msg = f"🎉 <b>G'alaba!</b>\n⚔️ {winner['team_name']} vs {loser['team_name']}\n{result_icon}"
    lose_msg = f"😔 <b>Mag'lubiyat</b>\n⚔️ {winner['team_name']} vs {loser['team_name']}"
    if rtype=="def": lose_msg += "\n🚫 Texnik mag'lubiyat"

    for p in db.get_team_players(wid):
        try: await bot.send_message(p["user_id"],win_msg,parse_mode="HTML")
        except: pass
    for p in db.get_team_players(lid):
        try: await bot.send_message(p["user_id"],lose_msg,parse_mode="HTML")
        except: pass

    # Guruh chatlarga ham
    for team, msg_text in [(winner,win_msg),(loser,lose_msg)]:
        if team.get("chat_id"):
            try: await bot.send_message(team["chat_id"],msg_text,parse_mode="HTML")
            except: pass

@router.callback_query(F.data.startswith("mvp_"))
async def set_mvp(call: CallbackQuery, bot: Bot):
    if not is_admin(call.from_user.id): return
    parts = call.data.split("_")
    mid, uid = int(parts[1]), int(parts[2])
    db.set_mvp(mid, uid)
    u = db.get_user(uid)
    name = (u.get("mlbb_nick") or u.get("username") or "?") if u else "?"
    await call.message.edit_text(f"⭐ <b>MVP: {name}</b>", parse_mode="HTML")
    try: await bot.send_message(uid,"⭐ <b>Tabriklaymiz! Siz MVP tanlandingiz!</b> 🎉",parse_mode="HTML")
    except: pass

@router.callback_query(F.data.startswith("skip_mvp_"))
async def skip_mvp(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    await call.message.edit_text("⏭ MVP o'tkazib yuborildi.")

# ── SCREENSHOTS ───────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_screenshots")
async def view_screenshots(call: CallbackQuery, bot: Bot):
    if not is_admin(call.from_user.id): return
    scs = db.get_pending_screenshots()
    if not scs: await call.answer("Screenshot yo'q!", show_alert=True); return
    for sc in scs[:5]:
        m = db.get_match(sc["match_id"])
        t1=db.get_team(m["team1_id"]) if m else None
        t2=db.get_team(m["team2_id"]) if m else None
        claimed=db.get_team(sc["claimed_winner"])
        cap = (f"📸 Match #{sc['match_id']}\n"
               +(f"⚔️ {t1['team_name']} vs {t2['team_name']}\n" if t1 and t2 else "")
               +f"🏆 Da'vo: {claimed['team_name'] if claimed else '?'}")
        try:
            await bot.send_photo(call.from_user.id, sc["file_id"], caption=cap,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"csc_{sc['id']}"),
                    InlineKeyboardButton(text="❌ Rad etish",  callback_data=f"rsc_{sc['id']}"),
                ]]))
        except: pass

@router.callback_query(F.data.startswith("csc_"))
async def confirm_sc(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    sc = db.confirm_screenshot(int(call.data.replace("csc_","")))
    if sc:
        claimed=db.get_team(sc["claimed_winner"]); m=db.get_match(sc["match_id"])
        if m and not m["winner_id"] and claimed:
            lid = m["team2_id"] if m["team1_id"]==claimed["id"] else m["team1_id"]
            db.submit_result(sc["match_id"],claimed["id"],lid)
    await call.answer("✅ Tasdiqlandi!"); await call.message.delete()

@router.callback_query(F.data.startswith("rsc_"))
async def reject_sc(call: CallbackQuery, bot: Bot):
    if not is_admin(call.from_user.id): return
    sc = db.delete_screenshot(int(call.data.replace("rsc_","")))
    if sc:
        try: await bot.send_message(sc["user_id"],"❌ Screenshot rad etildi. Qayta yuboring.")
        except: pass
    await call.answer("❌ Rad etildi!"); await call.message.delete()

# ── SUPPORT TICKETLAR ─────────────────────────────────────────────────

@router.callback_query(F.data == "adm_tickets")
async def adm_tickets(call: CallbackQuery, bot: Bot):
    if not is_admin(call.from_user.id): return
    tickets = db.get_open_tickets()
    if not tickets:
        await call.answer("Hali xabarlar yo'q!", show_alert=True); return
    for tk in tickets[:5]:
        btns = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"💬 Javob berish", callback_data=f"reply_tk_{tk['id']}"),
             InlineKeyboardButton(text="✅ Yopish",         callback_data=f"close_tk_{tk['id']}")],
        ])
        text = (f"📨 <b>Xabar #{tk['id']}</b>\n"
                f"👤 @{tk['username']} (ID: <code>{tk['user_id']}</code>)\n"
                f"🕐 {tk['created_at'][:16]}\n\n"
                f"💬 {tk['message']}")
        if tk.get("file_id") and tk.get("file_type")=="photo":
            try: await bot.send_photo(call.from_user.id, tk["file_id"], caption=text, reply_markup=btns, parse_mode="HTML")
            except: await call.message.answer(text, reply_markup=btns, parse_mode="HTML")
        elif tk.get("file_id") and tk.get("file_type")=="animation":
            try: await bot.send_animation(call.from_user.id, tk["file_id"], caption=text, reply_markup=btns, parse_mode="HTML")
            except: await call.message.answer(text, reply_markup=btns, parse_mode="HTML")
        else:
            await call.message.answer(text, reply_markup=btns, parse_mode="HTML")

@router.callback_query(F.data.startswith("reply_tk_"))
async def reply_ticket(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    tk_id = int(call.data.replace("reply_tk_",""))
    tk = db.get_ticket(tk_id)
    if not tk: return
    db.set_state(call.from_user.id,"admin_reply_ticket",{"ticket_id":tk_id,"user_id":tk["user_id"]})
    await call.message.answer(
        f"💬 <b>Javob yozing</b>\n\n"
        f"👤 @{tk['username']}\n"
        f"Savol: {tk['message']}\n\n"
        f"Javobingizni yuboring (matn, rasm yoki GIF):",
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("close_tk_"))
async def close_ticket(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    tk_id = int(call.data.replace("close_tk_",""))
    db.close_ticket(tk_id)
    await call.answer("✅ Yopildi!"); await call.message.delete()

# ── LIDERLARGA DM ─────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_dm_leaders")
async def dm_leaders(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    ts = db.get_active_tournaments()
    if not ts: await call.answer("Faol turnir yo'q!", show_alert=True); return
    t = ts[0]
    teams = db.get_teams_by_tournament(t["id"])
    if not teams: await call.answer("Hali jamoalar yo'q!", show_alert=True); return
    btns = [[InlineKeyboardButton(
        text=f"👑 {tm['team_name']}",
        callback_data=f"dm_one_{tm['leader_id']}"
    )] for tm in teams]
    btns.append([InlineKeyboardButton(text="📢 Barcha liderlarga", callback_data="dm_all_leaders")])
    btns.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="adm_back")])
    await call.message.edit_text(
        "📩 <b>Liderlarga xabar</b>\n\nQaysi liderga?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("dm_one_"))
async def dm_one(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    uid = int(call.data.replace("dm_one_",""))
    db.set_state(call.from_user.id,"admin_send_dm",{"target_id":uid})
    await call.message.answer("📨 Xabar yuboring (matn, rasm yoki GIF qo'shishingiz mumkin):")

@router.callback_query(F.data == "dm_all_leaders")
async def dm_all(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    ts = db.get_active_tournaments()
    if not ts: return
    teams = db.get_teams_by_tournament(ts[0]["id"])
    ids = list(set(tm["leader_id"] for tm in teams))
    db.set_state(call.from_user.id,"admin_send_dm",{"target_ids":ids})
    await call.message.answer(f"📢 {len(ids)} ta liderga xabar yuboring:")

# ── STATISTIKA ────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_stats")
async def adm_stats(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    conn=db.get_conn(); c=conn.cursor()
    c.execute("SELECT COUNT(*) as n FROM tournaments"); tt=c.fetchone()["n"]
    c.execute("SELECT COUNT(*) as n FROM teams"); tms=c.fetchone()["n"]
    c.execute("SELECT COUNT(*) as n FROM users"); us=c.fetchone()["n"]
    c.execute("SELECT COUNT(*) as n FROM matches WHERE status='finished'"); ms=c.fetchone()["n"]
    c.execute("SELECT COUNT(*) as n FROM support_tickets WHERE status='open'"); reqs=c.fetchone()["n"]
    conn.close()
    users=db.get_all_users()
    top=sorted(users,key=lambda x:x["total_wins"],reverse=True)[:3]
    top_txt=""
    medals=["🥇","🥈","🥉"]
    for i,u in enumerate(top):
        n=u.get("mlbb_nick") or u.get("username") or "?"
        top_txt+=f"{medals[i]} {n} — W:{u['total_wins']} ⭐{u['total_mvp']}\n"
    await call.message.answer(
        f"📊 <b>Umumiy statistika</b>\n\n"
        f"🏆 Turnirlar: {tt}\n👥 Jamoalar: {tms}\n"
        f"👤 Foydalanuvchilar: {us}\n⚔️ Matchlar: {ms}\n"
        f"📨 Ochiq xabarlar: {reqs}\n\n"
        f"🏅 <b>Top 3:</b>\n{top_txt}",
        parse_mode="HTML"
    )
