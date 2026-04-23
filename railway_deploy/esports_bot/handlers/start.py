from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
import database as db
from config import MLBB_RANKS, TOURNAMENT_FORMATS

router = Router()

async def check_channels(bot, uid):
    not_sub=[]
    for ch in db.get_channels():
        try:
            m=await bot.get_chat_member(ch["id"],uid)
            if m.status in ("left","kicked","banned"): not_sub.append(ch)
        except: not_sub.append(ch)
    return not_sub

@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    u=message.from_user
    db.register_user(u.id,u.username or "",u.first_name)
    not_sub=await check_channels(bot,u.id)
    if not_sub:
        btns=[[InlineKeyboardButton(text=f"➡️ {c['name']}",url=c["link"])] for c in not_sub if c.get("link")]
        btns.append([InlineKeyboardButton(text="✅ Tekshirish",callback_data="check_sub")])
        await message.answer(f"👋 Salom <b>{u.first_name}</b>!\n\n⚠️ Avval kanallarga a'zo bo'ling:",
                             reply_markup=InlineKeyboardMarkup(inline_keyboard=btns),parse_mode="HTML")
        return
    await show_main(message,u)

@router.callback_query(F.data=="check_sub")
async def check_sub(call: CallbackQuery, bot: Bot):
    not_sub=await check_channels(bot,call.from_user.id)
    if not_sub: await call.answer("❌ Hali a'zo emassiz!",show_alert=True); return
    await call.message.delete()
    await show_main(call.message,call.from_user)

async def show_main(message, user):
    ts=db.get_active_tournaments()
    btns=[]
    if ts:
        for t in ts:
            icon={"reg":"✍️","checkin":"✅","online":"⚔️","offline":"🏟️"}.get(t["status"],"🏆")
            btns.append([InlineKeyboardButton(text=f"{icon} {t['title']}",callback_data=f"t_{t['id']}")])
    btns.append([
        InlineKeyboardButton(text="👤 Profilim",callback_data="my_profile"),
        InlineKeyboardButton(text="📊 Top",callback_data="top_stats"),
    ])
    btns.append([InlineKeyboardButton(text="📨 Adminga xabar",callback_data="contact_admin")])
    text=(f"🏆 <b>MLBB Turnir Bot</b>\n\n👋 <b>{user.first_name}</b>!\n\n"
          +("📋 <b>Faol turnirlar:</b>" if ts else "📭 Hozircha turnir yo'q."))
    await message.answer(text,reply_markup=InlineKeyboardMarkup(inline_keyboard=btns),parse_mode="HTML")

@router.callback_query(F.data=="my_profile")
async def my_profile(call: CallbackQuery):
    u=db.get_user(call.from_user.id)
    if not u: await call.answer("Profil topilmadi!"); return
    wr=round(u["total_wins"]/(u["total_wins"]+u["total_losses"])*100) if u["total_wins"]+u["total_losses"]>0 else 0
    text=(f"👤 <b>Mening profilim</b>\n\n"
          f"📛 {call.from_user.first_name}\n"
          f"🎮 Nick: {u.get('mlbb_nick') or '—'}\n"
          f"🆔 MLBB ID: {u.get('mlbb_id') or '—'}\n"
          f"🏅 Rank: {u.get('rank') or '—'}\n"
          f"🏫 Maktab: {u.get('school') or '—'}\n\n"
          f"✅ G'alaba: {u['total_wins']} | ❌ Mag'lubiyat: {u['total_losses']}\n"
          f"📊 Win Rate: {wr}%\n"
          f"⭐ MVP: {u['total_mvp']} marta\n"
          f"🏆 Turnirlar: {u['tournaments_played']}")
    btns=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Yangilash",callback_data="edit_profile")],
        [InlineKeyboardButton(text="◀️ Orqaga",callback_data="back_main")],
    ])
    await call.message.edit_text(text,reply_markup=btns,parse_mode="HTML")

@router.callback_query(F.data=="edit_profile")
async def edit_profile(call: CallbackQuery):
    db.set_state(call.from_user.id,"profile_mlbb_id",{})
    await call.message.answer("✏️ MLBB ID ingizni yuboring:")

@router.callback_query(F.data=="top_stats")
async def top_stats(call: CallbackQuery):
    users=db.get_all_users()
    if not users: await call.answer("Hali statistika yo'q!"); return
    top=sorted(users,key=lambda x:x["total_wins"],reverse=True)[:10]
    text="🏅 <b>Top 10 o'yinchilar</b>\n\n"
    medals=["🥇","🥈","🥉"]
    for i,u in enumerate(top,1):
        m=medals[i-1] if i<=3 else f"{i}."
        n=u.get("mlbb_nick") or u.get("username") or "?"
        wr=round(u["total_wins"]/(u["total_wins"]+u["total_losses"])*100) if u["total_wins"]+u["total_losses"]>0 else 0
        text+=f"{m} <b>{n}</b> | W:{u['total_wins']} WR:{wr}% ⭐{u['total_mvp']}\n"
    await call.message.answer(text,parse_mode="HTML")

@router.callback_query(F.data.startswith("t_"))
async def tournament_page(call: CallbackQuery):
    try: tid=int(call.data.split("_")[1])
    except: return
    t=db.get_tournament(tid)
    if not t: return
    teams=db.get_teams_by_tournament(tid)
    user_team=db.get_user_team(call.from_user.id,tid)
    is_reg=user_team is not None
    fmt=TOURNAMENT_FORMATS.get(t["format"],t["format"])
    status_txt={"reg":"✍️ Ro'yxat ochiq","checkin":"✅ Check-in","online":"⚔️ Online","offline":"🏟️ Offline"}.get(t["status"],"—")
    deadline_txt=""
    if t.get("reg_deadline"):
        try:
            from datetime import datetime
            dl=datetime.fromisoformat(t["reg_deadline"])
            deadline_txt=f"\n⏰ Deadline: {dl.strftime('%d.%m.%Y %H:%M')}"
        except: pass
    text=(f"🏆 <b>{t['title']}</b>\n━━━━━━━━━━━━━━━\n"
          f"📌 {status_txt}\n🎮 {fmt}\n"
          f"👥 Jamoalar: {len(teams)}/{t['max_teams']}{deadline_txt}\n"
          f"💰 {t.get('prize_pool') or '—'}\n"
          +(f"🥇 {t['prize_distribution']}\n" if t.get("prize_distribution") else "")
          +(f"\n📝 {t['description']}\n" if t.get("description") else ""))
    btns=[[InlineKeyboardButton(text="📋 Qoidalar",callback_data=f"rules_{tid}"),
           InlineKeyboardButton(text="📊 Jadval",callback_data=f"bracket_{tid}")]]
    if t["status"]=="reg":
        if not is_reg: btns.append([InlineKeyboardButton(text="✍️ Ro'yxatdan o'tish",callback_data=f"register_{tid}")])
        else: btns.append([InlineKeyboardButton(text="👥 Mening jamoam",callback_data=f"myteam_{tid}")])
    elif t["status"]=="checkin":
        if is_reg:
            if not user_team.get("checked_in"): btns.append([InlineKeyboardButton(text="✅ Check-in",callback_data=f"checkin_{tid}")])
            else: btns.append([InlineKeyboardButton(text="✔️ Check-in qilingan",callback_data="noop")])
        if is_reg: btns.append([InlineKeyboardButton(text="👥 Mening jamoam",callback_data=f"myteam_{tid}")])
    elif t["status"] in ("online","offline"):
        if is_reg: btns.append([InlineKeyboardButton(text="👥 Mening jamoam",callback_data=f"myteam_{tid}")])
    # Banner bor bo'lsa rasm bilan jo'nat
    if t.get("banner_file_id"):
        try: await call.message.answer_photo(t["banner_file_id"],caption=text,reply_markup=InlineKeyboardMarkup(inline_keyboard=btns),parse_mode="HTML"); return
        except: pass
    await call.message.edit_text(text,reply_markup=InlineKeyboardMarkup(inline_keyboard=btns),parse_mode="HTML")

@router.callback_query(F.data.startswith("rules_"))
async def show_rules(call: CallbackQuery):
    tid=int(call.data.split("_")[1])
    t=db.get_tournament(tid)
    rules=t.get("rules") or "Belgilanmagan."
    default=(f"📜 <b>Qoidalar</b>\n\n"
             "1️⃣ Har jamoa 5 o'yinchidan\n2️⃣ Custom Room da o'ynalinadi\n"
             "3️⃣ Natija screenshotini botga yuboring\n4️⃣ Kechikish 10 daqiqa → texnik mag'lubiyat\n"
             "5️⃣ Admin qarori qat'iy\n6️⃣ Haqorat → disqualifikatsiya\n\n"
             f"📌 {rules}")
    await call.message.answer(default,parse_mode="HTML")

@router.callback_query(F.data.startswith("bracket_"))
async def show_bracket(call: CallbackQuery):
    tid=int(call.data.split("_")[1])
    teams=db.get_teams_by_tournament(tid)
    matches=db.get_finished_matches(tid)
    if not teams: await call.answer("Hali jamoalar yo'q!",show_alert=True); return
    text="📊 <b>Turnir Jadvali</b>\n\n👥 <b>Jamoalar:</b>\n"
    icons={"complete":"✅","pending":"⏳","eliminated":"❌","winner":"🏆","checked_in":"✔️"}
    for i,tm in enumerate(teams,1):
        text+=f"{i}. {icons.get(tm['status'],'•')} <b>{tm['team_name']}</b> [{tm.get('school','—')}] — W:{tm['wins']} L:{tm['losses']}\n"
    if matches:
        text+="\n⚔️ <b>Oxirgi matchlar:</b>\n"
        for m in matches[-5:]:
            t1=db.get_team(m["team1_id"]); t2=db.get_team(m["team2_id"]); w=db.get_team(m["winner_id"]) if m["winner_id"] else None
            rtype=" (DEF)" if m.get("result_type")=="def" else ""
            if t1 and t2:
                line=f"• {t1['team_name']} vs {t2['team_name']}"
                if w: line+=f" → 🏆 {w['team_name']}{rtype}"
                text+=line+"\n"
    await call.message.answer(text,parse_mode="HTML")

@router.callback_query(F.data.startswith("checkin_"))
async def checkin(call: CallbackQuery):
    tid=int(call.data.split("_")[1])
    team=db.get_user_team(call.from_user.id,tid)
    if not team: await call.answer("Ro'yxatda emassiz!",show_alert=True); return
    if team.get("checked_in"): await call.answer("Allaqachon check-in!",show_alert=True); return
    if team["leader_id"]!=call.from_user.id: await call.answer("Faqat lider check-in qiladi!",show_alert=True); return
    db.checkin_team(team["id"])
    await call.answer("✅ Check-in qilindi!",show_alert=True)
    await call.message.answer(f"✅ <b>{team['team_name']}</b> — check-in!\n\nLobby kelishini kuting. ⚔️",parse_mode="HTML")

@router.callback_query(F.data=="back_main")
async def back_main(call: CallbackQuery):
    await show_main(call.message,call.from_user)

@router.callback_query(F.data=="noop")
async def noop(call: CallbackQuery): await call.answer()

@router.callback_query(F.data=="contact_admin")
async def contact_admin_btn(call: CallbackQuery):
    db.set_state(call.from_user.id,"support_msg",{})
    await call.message.answer(
        "📨 <b>Adminga xabar yuborish</b>\n\n"
        "Xabaringizni yuboring.\n"
        "• Matn\n• Rasm (caption bilan)\n• GIF\n\n"
        "<i>Admin tez orada javob beradi.</i>",
        parse_mode="HTML"
    )
