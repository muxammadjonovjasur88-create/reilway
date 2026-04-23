from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
import database as db
from config import MLBB_LANES, MLBB_RANKS, ADMIN_IDS

router = Router()

def lanes_kb(exclude=None):
    ex = exclude or []
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=l, callback_data=f"lane_{l}")] for l in MLBB_LANES if l not in ex
    ])

def ranks_kb():
    rows=[]
    for i in range(0,len(MLBB_RANKS),2):
        row=[InlineKeyboardButton(text=MLBB_RANKS[i],callback_data=f"rank_{MLBB_RANKS[i]}")]
        if i+1<len(MLBB_RANKS): row.append(InlineKeyboardButton(text=MLBB_RANKS[i+1],callback_data=f"rank_{MLBB_RANKS[i+1]}"))
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ── RO'YXATDAN O'TISH ─────────────────────────────────────────────────

@router.callback_query(F.data.startswith("register_"))
async def start_reg(call: CallbackQuery):
    tid = int(call.data.split("_")[1])
    t = db.get_tournament(tid)
    if t["status"]!="reg": await call.answer("Ro'yxat hozir ochiq emas!", show_alert=True); return
    if db.get_user_team(call.from_user.id,tid): await call.answer("Allaqachon ro'yxatdansiz!", show_alert=True); return
    db.set_state(call.from_user.id,"reg_school",{"tournament_id":tid})
    await call.message.answer(
        "✍️ <b>Ro'yxatdan o'tish</b>\n\n"
        "🏫 Maktabingizni kiriting:\n<i>Masalan: 5-maktab, Najot IT</i>",
        parse_mode="HTML"
    )

# ── TEXT HANDLER ──────────────────────────────────────────────────────

@router.message(F.photo)
async def handle_photo(message: Message, bot: Bot):
    state, data = db.get_state(message.from_user.id)
    file_id = message.photo[-1].file_id

    if state == "submit_screenshot":
        db.submit_screenshot(data["match_id"],data["team_id"],message.from_user.id,file_id,data.get("claimed_winner_id"))
        db.clear_state(message.from_user.id)
        await message.answer("📸 <b>Screenshot yuborildi!</b>\nAdmin tekshiradi. ⏳", parse_mode="HTML")

    elif state == "support_msg":
        # O'yinchi adminlarga rasm yubormoqda
        data["file_id"]=file_id; data["file_type"]="photo"
        msg_text = message.caption or data.get("message","Rasm yuborildi")
        tk_id = db.create_ticket(message.from_user.id, message.from_user.username or "", msg_text, file_id, "photo")
        db.clear_state(message.from_user.id)
        await message.answer("✅ <b>Xabar adminga yuborildi!</b>\nJavob kelishini kuting.", parse_mode="HTML")
        for aid in ADMIN_IDS:
            try: await bot.send_message(aid,f"📨 Yangi xabar #{tk_id}\n@{message.from_user.username or message.from_user.first_name}")
            except: pass

    elif state == "admin_banner":
        tid = data.get("tournament_id")
        db.set_tournament_banner(tid, file_id)
        db.clear_state(message.from_user.id)
        await message.answer("✅ Banner saqlandi!")

    elif state in ("admin_broadcast_media","admin_reply_ticket","admin_send_dm"):
        await handle_admin_media(message, bot, state, data, file_id, "photo")

@router.message(F.animation)
async def handle_animation(message: Message, bot: Bot):
    state, data = db.get_state(message.from_user.id)
    file_id = message.animation.file_id

    if state == "support_msg":
        msg_text = message.caption or data.get("message","GIF yuborildi")
        tk_id = db.create_ticket(message.from_user.id, message.from_user.username or "", msg_text, file_id, "animation")
        db.clear_state(message.from_user.id)
        await message.answer("✅ <b>GIF bilan xabar adminga yuborildi!</b>", parse_mode="HTML")
        for aid in ADMIN_IDS:
            try: await bot.send_message(aid,f"📨 Yangi xabar #{tk_id} (GIF)\n@{message.from_user.username or message.from_user.first_name}")
            except: pass

    elif state in ("admin_broadcast_media","admin_reply_ticket","admin_send_dm"):
        await handle_admin_media(message, bot, state, data, file_id, "animation")

async def handle_admin_media(message, bot, state, data, file_id, media_type):
    caption = message.caption or ""
    if state == "admin_broadcast_media":
        users = db.get_all_users()
        sent=0
        for u in users:
            try:
                if media_type=="photo": await bot.send_photo(u["user_id"],file_id,caption=f"📢 {caption}",parse_mode="HTML"); sent+=1
                else: await bot.send_animation(u["user_id"],file_id,caption=f"📢 {caption}",parse_mode="HTML"); sent+=1
            except: pass
        db.clear_state(message.from_user.id)
        await message.answer(f"✅ {sent} ta foydalanuvchiga yuborildi!")

    elif state == "admin_reply_ticket":
        tk_id = data.get("ticket_id"); uid = data.get("user_id")
        db.close_ticket(tk_id, caption or "Media javob")
        try:
            if media_type=="photo": await bot.send_photo(uid,file_id,caption=f"💬 <b>Admin javobi:</b>\n{caption}",parse_mode="HTML")
            else: await bot.send_animation(uid,file_id,caption=f"💬 <b>Admin javobi:</b>\n{caption}",parse_mode="HTML")
        except: pass
        db.clear_state(message.from_user.id)
        await message.answer("✅ Javob yuborildi!")

    elif state == "admin_send_dm":
        targets = data.get("target_ids") or ([data["target_id"]] if data.get("target_id") else [])
        sent=0
        for uid in targets:
            try:
                if media_type=="photo": await bot.send_photo(uid,file_id,caption=f"📨 <b>Admin xabari:</b>\n{caption}",parse_mode="HTML"); sent+=1
                else: await bot.send_animation(uid,file_id,caption=f"📨 <b>Admin xabari:</b>\n{caption}",parse_mode="HTML"); sent+=1
            except: pass
        db.clear_state(message.from_user.id)
        await message.answer(f"✅ {sent} ta odamga yuborildi!")

@router.message(F.text)
async def handle_text(message: Message, bot: Bot):
    state, data = db.get_state(message.from_user.id)
    if not state: return
    txt = message.text.strip()

    # ── PROFIL ────────────────────────────────────────────────────────
    if state=="profile_mlbb_id":
        if not txt.isdigit() or len(txt)<6: await message.answer("❌ MLBB ID faqat raqam (kamida 6 ta)."); return
        data["mlbb_id"]=txt; db.set_state(message.from_user.id,"profile_mlbb_nick",data)
        await message.answer("🎮 MLBB Nick nomingizni yuboring:")
    elif state=="profile_mlbb_nick":
        data["mlbb_nick"]=txt; db.set_state(message.from_user.id,"profile_rank",data)
        await message.answer("🏅 Rankingizni tanlang:", reply_markup=ranks_kb())

    # ── SUPPORT ───────────────────────────────────────────────────────
    elif state=="support_msg":
        data["message"]=txt
        tk_id = db.create_ticket(message.from_user.id, message.from_user.username or "", txt)
        db.clear_state(message.from_user.id)
        await message.answer("✅ <b>Xabar adminga yuborildi!</b>\nJavob kelishini kuting. ⏳", parse_mode="HTML")
        for aid in ADMIN_IDS:
            try:
                await bot.send_message(aid,
                    f"📨 <b>Yangi xabar #{tk_id}</b>\n"
                    f"👤 @{message.from_user.username or message.from_user.first_name}\n"
                    f"ID: <code>{message.from_user.id}</code>\n\n"
                    f"💬 {txt}",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="💬 Javob", callback_data=f"reply_tk_{tk_id}"),
                         InlineKeyboardButton(text="✅ Yopish", callback_data=f"close_tk_{tk_id}")]
                    ]),
                    parse_mode="HTML")
            except: pass

    # ── ADMIN REPLY TICKET ────────────────────────────────────────────
    elif state=="admin_reply_ticket":
        tk_id=data.get("ticket_id"); uid=data.get("user_id")
        db.close_ticket(tk_id, txt)
        try:
            await bot.send_message(uid,
                f"💬 <b>Admin javobi:</b>\n\n{txt}",
                parse_mode="HTML")
        except: pass
        db.clear_state(message.from_user.id)
        await message.answer("✅ Javob yuborildi!")

    # ── ADMIN DM ──────────────────────────────────────────────────────
    elif state=="admin_send_dm":
        targets = data.get("target_ids") or ([data["target_id"]] if data.get("target_id") else [])
        sent=0
        for uid in targets:
            try:
                await bot.send_message(uid,
                    f"📨 <b>Admin xabari:</b>\n\n{txt}",
                    parse_mode="HTML"); sent+=1
            except: pass
        db.clear_state(message.from_user.id)
        await message.answer(f"✅ {sent} ta odamga yuborildi!")

    # ── BROADCAST ─────────────────────────────────────────────────────
    elif state=="admin_broadcast_media":
        users=db.get_all_users(); sent=0
        for u in users:
            try: await bot.send_message(u["user_id"],f"📢 <b>E'lon</b>\n\n{txt}",parse_mode="HTML"); sent+=1
            except: pass
        db.clear_state(message.from_user.id)
        await message.answer(f"✅ {sent} ta foydalanuvchiga yuborildi!")

    # ── KANAL ─────────────────────────────────────────────────────────
    elif state=="admin_add_channel":
        parts=txt.split(None,1)
        if len(parts)<2: await message.answer("❌ Format: <code>-1001234567890 Kanal nomi</code>",parse_mode="HTML"); return
        try: cid=int(parts[0])
        except: await message.answer("❌ ID raqam bo'lishi kerak!"); return
        db.add_channel(cid,parts[1]); db.clear_state(message.from_user.id)
        await message.answer(f"✅ <b>{parts[1]}</b> qo'shildi!",parse_mode="HTML")

    # ── TURNIR YARATISH ───────────────────────────────────────────────
    elif state=="admin_title":
        if txt.startswith("/"): return
        data["title"]=txt; db.set_state(message.from_user.id,"admin_desc",data)
        await message.answer("📝 Tavsif (yoki /skip):")
    elif state=="admin_desc":
        data["description"]="" if txt=="/skip" else txt
        db.set_state(message.from_user.id,"admin_prize",data)
        await message.answer("💰 Sovrin miqdori:")
    elif state=="admin_prize":
        data["prize_pool"]=txt; db.set_state(message.from_user.id,"admin_prize_dist",data)
        await message.answer("🥇 Sovrin taqsimoti (yoki /skip):")
    elif state=="admin_prize_dist":
        data["prize_distribution"]="" if txt=="/skip" else txt
        db.set_state(message.from_user.id,"admin_max_teams",data)
        await message.answer("👥 Maksimal jamoalar soni:")
    elif state=="admin_max_teams":
        if not txt.isdigit(): await message.answer("❌ Faqat raqam!"); return
        data["max_teams"]=int(txt); db.set_state(message.from_user.id,"admin_rules",data)
        await message.answer("📜 Qoidalar (yoki /skip):")
    elif state=="admin_rules":
        data["rules"]="" if txt=="/skip" else txt
        db.set_state(message.from_user.id,"admin_deadline",data)
        await message.answer("⏰ Deadline (yoki /skip)\nFormat: <code>2026-05-25 23:59</code>",parse_mode="HTML")
    elif state=="admin_deadline":
        from datetime import datetime as dt
        if txt=="/skip": data["deadline_iso"]=""; data["deadline_text"]="—"
        else:
            try: dl=dt.strptime(txt,"%Y-%m-%d %H:%M"); data["deadline_iso"]=dl.isoformat(); data["deadline_text"]=dl.strftime("%d.%m.%Y %H:%M")
            except: await message.answer("❌ Format: <code>2026-05-25 23:59</code>",parse_mode="HTML"); return
        db.set_state(message.from_user.id,"admin_confirm",data)
        from config import TOURNAMENT_FORMATS
        await message.answer(
            f"📋 <b>Turnir:</b>\n\n🏆 {data['title']}\n🎮 {TOURNAMENT_FORMATS.get(data.get('format','single'))}\n"
            f"💰 {data.get('prize_pool')}\n👥 Max: {data['max_teams']}\n⏰ {data.get('deadline_text','—')}\n\nYaratilsinmi?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="✅ Yaratish",callback_data="confirm_create_t"),
                InlineKeyboardButton(text="❌ Bekor",callback_data="cancel_admin"),
            ]]),parse_mode="HTML"
        )

    # ── OFFLINE ───────────────────────────────────────────────────────
    elif state=="admin_offline_location":
        data["location"]=txt; db.set_state(message.from_user.id,"admin_offline_date",data)
        await message.answer("📅 Sana va vaqt kiriting:")
    elif state=="admin_offline_date":
        db.update_tournament(data["tournament_id"],offline_location=data["location"],offline_date=txt)
        db.clear_state(message.from_user.id)
        await message.answer(f"✅ Saqlandi!\n📍 {data['location']}\n📅 {txt}")

    # ── MAKTAB VA JAMOA ───────────────────────────────────────────────
    elif state=="reg_school":
        school = txt
        data["school"]=school
        tid=data["tournament_id"]
        t=db.get_tournament(tid)
        # O'sha maktabdagi jamoalarni ko'rsat
        teams = db.get_teams_by_tournament(tid)
        open_teams = [tm for tm in teams if tm.get("school","").lower()==school.lower()
                      and tm["status"] in ("pending",)
                      and len(db.get_team_players(tm["id"]))<t.get("team_size",5)]

        db.set_state(message.from_user.id,"choose_action",data)
        btns=[]
        for tm in open_teams[:6]:
            players=db.get_team_players(tm["id"])
            missing=db.get_team_missing_lanes(tm["id"])
            missing_txt=", ".join([l.split()[-1] for l in missing]) if missing else "To'liq"
            btns.append([InlineKeyboardButton(
                text=f"👥 {tm['team_name']} ({len(players)}/{t.get('team_size',5)}) | Bo'sh: {missing_txt}",
                callback_data=f"view_team_{tm['id']}"
            )])
        btns.append([InlineKeyboardButton(text="➕ Yangi jamoa ochish", callback_data=f"new_team_{tid}")])

        txt_out=(f"🏫 <b>{school}</b> maktabi\n\n"
                 +(f"Quyidagi jamoalar mavjud:\n<i>Bo'sh liniyalar ko'rinadi</i>" if open_teams else "Bu maktabdan hali ochiq jamoa yo'q."))
        await message.answer(txt_out, reply_markup=InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")

    elif state=="reg_team_name":
        if txt.startswith("/"): return
        if len(txt)<2 or len(txt)>30: await message.answer("❌ Jamoa nomi 2-30 belgi."); return
        data["team_name"]=txt
        u=db.get_user(message.from_user.id)
        if u and u.get("mlbb_id"):
            data["mlbb_id"]=u["mlbb_id"]; data["mlbb_nick"]=u["mlbb_nick"]; data["rank"]=u.get("rank","")
            db.set_state(message.from_user.id,"reg_use_profile",data)
            await message.answer(
                f"✅ Jamoa: <b>{txt}</b>\n\nSaqlangan profil: {u['mlbb_nick']} ({u['mlbb_id']})\nShu bilan ro'yxatdan o'tasizmi?",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Ha",callback_data="reg_use_saved")],
                    [InlineKeyboardButton(text="✏️ Yangi",callback_data="reg_enter_new")],
                ]),parse_mode="HTML"
            )
        else:
            db.set_state(message.from_user.id,"reg_mlbb_id",data)
            await message.answer("🎮 MLBB ID ingizni yuboring:")

    elif state=="reg_mlbb_id":
        if not txt.isdigit() or len(txt)<6: await message.answer("❌ Noto'g'ri MLBB ID."); return
        data["mlbb_id"]=txt; db.set_state(message.from_user.id,"reg_mlbb_nick",data)
        await message.answer("🎮 MLBB Nick nomingizni yuboring:")
    elif state=="reg_mlbb_nick":
        data["mlbb_nick"]=txt; db.set_state(message.from_user.id,"reg_rank",data)
        await message.answer("🏅 Rankingizni tanlang:", reply_markup=ranks_kb())

    elif state=="join_req_mlbb_id":
        if not txt.isdigit() or len(txt)<6: await message.answer("❌ Noto'g'ri MLBB ID."); return
        data["mlbb_id"]=txt; db.set_state(message.from_user.id,"join_req_mlbb_nick",data)
        await message.answer("🎮 MLBB Nick:")
    elif state=="join_req_mlbb_nick":
        data["mlbb_nick"]=txt; db.set_state(message.from_user.id,"join_req_rank",data)
        await message.answer("🏅 Rankingizni tanlang:", reply_markup=ranks_kb())

# ── CALLBACKS ─────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("view_team_"))
async def view_team(call: CallbackQuery):
    team_id=int(call.data.replace("view_team_",""))
    team=db.get_team(team_id); t=db.get_tournament(team["tournament_id"])
    players=db.get_team_players(team_id)
    missing=db.get_team_missing_lanes(team_id)
    player_txt="".join(f"  {'👑' if p['is_leader'] else '•'} {p.get('mlbb_nick') or p['username']} — {p['lane']}\n" for p in players)
    missing_txt="\n".join(f"  • {l}" for l in missing) if missing else "  (To'liq)"
    await call.message.answer(
        f"👥 <b>{team['team_name']}</b>\n🏫 {team.get('school','—')}\n"
        f"━━━━━━━━━━━━━━━\nA'zolar: {len(players)}/{t.get('team_size',5)}\n{player_txt}"
        f"━━━━━━━━━━━━━━━\n🔸 Bo'sh liniyalar:\n{missing_txt}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📨 Qo'shilish so'rovi", callback_data=f"request_join_{team_id}")],
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data=f"register_{team['tournament_id']}")],
        ]),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("new_team_"))
async def new_team(call: CallbackQuery):
    tid=int(call.data.replace("new_team_",""))
    _,data=db.get_state(call.from_user.id)
    data["tournament_id"]=tid
    db.set_state(call.from_user.id,"reg_team_name",data)
    await call.message.answer("✍️ <b>Jamoa nomini yuboring:</b>",parse_mode="HTML")

@router.callback_query(F.data.startswith("request_join_"))
async def request_join(call: CallbackQuery):
    team_id=int(call.data.replace("request_join_",""))
    team=db.get_team(team_id)
    if db.get_user_team(call.from_user.id,team["tournament_id"]): await call.answer("Allaqachon jamoadadasiz!",show_alert=True); return
    if db.get_user_pending_request(call.from_user.id,team["tournament_id"]): await call.answer("Allaqachon so'rov yubordingiz!",show_alert=True); return
    u=db.get_user(call.from_user.id)
    _,data=db.get_state(call.from_user.id)
    data["team_id"]=team_id
    if u and u.get("mlbb_id"):
        await call.message.answer(
            f"📝 <b>{team['team_name']}</b> — So'rov yuborish\n\nSaqlangan profil: {u['mlbb_nick']} ({u['mlbb_id']})\nShu profil bilan?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Ha",callback_data=f"quick_req_{team_id}")],
                [InlineKeyboardButton(text="✏️ Yangi ma'lumot",callback_data=f"new_req_{team_id}")],
            ]),parse_mode="HTML"
        )
        db.set_state(call.from_user.id,"join_req_ready",data)
    else:
        db.set_state(call.from_user.id,"join_req_mlbb_id",data)
        await call.message.answer("🎮 MLBB ID ingizni yuboring:")

@router.callback_query(F.data.startswith("quick_req_"))
async def quick_req(call: CallbackQuery):
    team_id=int(call.data.replace("quick_req_",""))
    u=db.get_user(call.from_user.id)
    _,data=db.get_state(call.from_user.id)
    data.update({"mlbb_id":u["mlbb_id"],"mlbb_nick":u["mlbb_nick"],"rank":u.get("rank",""),"team_id":team_id})
    missing=db.get_team_missing_lanes(team_id)
    db.set_state(call.from_user.id,"join_req_lane",data)
    await call.message.answer("📍 Qaysi liniyada o'ynaysiz?", reply_markup=lanes_kb(exclude=[l for l in MLBB_LANES if l not in missing]))

@router.callback_query(F.data.startswith("new_req_"))
async def new_req(call: CallbackQuery):
    team_id=int(call.data.replace("new_req_",""))
    _,data=db.get_state(call.from_user.id)
    data["team_id"]=team_id; db.set_state(call.from_user.id,"join_req_mlbb_id",data)
    await call.message.answer("🎮 MLBB ID ingizni yuboring:")

@router.callback_query(F.data.startswith("rank_"))
async def select_rank(call: CallbackQuery):
    rank=call.data.replace("rank_","")
    state,data=db.get_state(call.from_user.id)
    data["rank"]=rank
    if state=="reg_rank":
        db.set_state(call.from_user.id,"reg_lane",data)
        await call.message.answer(f"✅ Rank: <b>{rank}</b>\n\n📍 Liniyangizni tanlang:", reply_markup=lanes_kb(),parse_mode="HTML")
    elif state=="join_req_rank":
        missing=db.get_team_missing_lanes(data.get("team_id",0))
        db.set_state(call.from_user.id,"join_req_lane",data)
        await call.message.answer("📍 Liniyangizni tanlang:", reply_markup=lanes_kb(exclude=[l for l in MLBB_LANES if l not in missing]))
    elif state=="profile_rank":
        db.update_user_profile(call.from_user.id,data["mlbb_id"],data["mlbb_nick"],rank,data.get("school",""))
        db.clear_state(call.from_user.id)
        await call.message.edit_text(f"✅ <b>Profil yangilandi!</b>\n🎮 {data['mlbb_nick']} | 🏅 {rank}",parse_mode="HTML")

@router.callback_query(F.data.startswith("lane_"))
async def select_lane(call: CallbackQuery):
    lane=call.data.replace("lane_","")
    state,data=db.get_state(call.from_user.id)
    data["lane"]=lane
    if state=="reg_lane":
        db.set_state(call.from_user.id,"reg_confirm",data)
        await call.message.edit_text(
            f"✅ <b>Tasdiqlang:</b>\n\n👥 Jamoa: <b>{data.get('team_name','')}</b>\n🏫 {data.get('school','')}\n"
            f"🎮 Nick: <b>{data.get('mlbb_nick','')}</b>\n🆔 ID: <code>{data.get('mlbb_id','')}</code>\n"
            f"🏅 Rank: <b>{data.get('rank','')}</b>\n📍 Liniya: <b>{lane}</b>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="✅ Tasdiqlash",callback_data=f"confirm_reg_{data['tournament_id']}"),
                InlineKeyboardButton(text="❌ Bekor",callback_data="cancel_reg"),
            ]]),parse_mode="HTML"
        )
    elif state=="join_req_lane":
        data["lane"]=lane; db.set_state(call.from_user.id,"join_req_confirm",data)
        team=db.get_team(data["team_id"])
        await call.message.edit_text(
            f"📝 <b>So'rov:</b>\n\n👥 {team['team_name']}\n🎮 {data.get('mlbb_nick','')}\n"
            f"🆔 <code>{data.get('mlbb_id','')}</code>\n🏅 {data.get('rank','')}\n📍 {lane}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="📨 Yuborish",callback_data=f"send_req_{data['team_id']}"),
                InlineKeyboardButton(text="❌ Bekor",callback_data="cancel_reg"),
            ]]),parse_mode="HTML"
        )

@router.callback_query(F.data == "reg_use_saved")
async def reg_use_saved(call: CallbackQuery):
    _,data=db.get_state(call.from_user.id)
    db.set_state(call.from_user.id,"reg_lane",data)
    await call.message.answer("📍 Liniyangizni tanlang:", reply_markup=lanes_kb())

@router.callback_query(F.data == "reg_enter_new")
async def reg_enter_new(call: CallbackQuery):
    _,data=db.get_state(call.from_user.id)
    db.set_state(call.from_user.id,"reg_mlbb_id",data)
    await call.message.answer("🎮 MLBB ID ingizni yuboring:")

@router.callback_query(F.data.startswith("confirm_reg_"))
async def confirm_reg(call: CallbackQuery):
    tid=int(call.data.split("_")[2])
    _,data=db.get_state(call.from_user.id)
    username=call.from_user.username or call.from_user.first_name
    db.register_user(call.from_user.id,username,call.from_user.first_name)
    db.update_user_profile(call.from_user.id,data["mlbb_id"],data["mlbb_nick"],data.get("rank",""),data.get("school",""))
    team_id,res=db.create_team(tid,data["team_name"],data.get("school",""),call.from_user.id,username)
    if res=="already": await call.answer("Allaqachon jamoadadasiz!",show_alert=True); return
    db.add_player_direct(team_id,call.from_user.id,username,data["mlbb_id"],data["mlbb_nick"],data["lane"],data.get("rank",""),data.get("school",""),is_leader=1)
    db.clear_state(call.from_user.id)
    t=db.get_tournament(tid)
    await call.message.edit_text(
        f"🎉 <b>Muvaffaqiyatli ro'yxatdan o'tdingiz!</b>\n\n"
        f"👥 Jamoa: <b>{data['team_name']}</b>\n🏫 {data.get('school','')}\n📍 {data['lane']}\n\n"
        f"Qolgan {t.get('team_size',5)-1} o'yinchi ro'yxatdan o'tib jamoangizni tanlashsin!\n"
        f"Yoki ularning so'rovlarini siz tasdiqlaysiz 👑",
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("send_req_"))
async def send_req(call: CallbackQuery, bot: Bot):
    team_id=int(call.data.replace("send_req_",""))
    _,data=db.get_state(call.from_user.id)
    username=call.from_user.username or call.from_user.first_name
    db.register_user(call.from_user.id,username,call.from_user.first_name)
    req_id,res=db.create_join_request(team_id,call.from_user.id,username,
        data["mlbb_id"],data["mlbb_nick"],data["lane"],data.get("rank",""),data.get("school",""))
    if res=="already_requested": await call.answer("Allaqachon so'rov yubordingiz!",show_alert=True); return
    db.clear_state(call.from_user.id)
    team=db.get_team(team_id)
    await call.message.edit_text(
        f"📨 <b>So'rov yuborildi!</b>\n\n👥 {team['team_name']}\n📍 {data['lane']}\n\nLiderning javobini kuting. ⏳",
        parse_mode="HTML"
    )
    try:
        await bot.send_message(team["leader_id"],
            f"📨 <b>Yangi qo'shilish so'rovi!</b>\n\n"
            f"👤 {data.get('mlbb_nick') or username} | 🏅 {data.get('rank','')}\n"
            f"📍 Liniya: {data['lane']}\n🆔 MLBB ID: {data['mlbb_id']}\n"
            f"🏫 Maktab: {data.get('school','—')}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="✅ Qabul",callback_data=f"acc_req_{req_id}"),
                InlineKeyboardButton(text="❌ Rad",callback_data=f"rej_req_{req_id}"),
            ]]),parse_mode="HTML"
        )
    except: pass

@router.callback_query(F.data.startswith("acc_req_"))
async def accept_req(call: CallbackQuery, bot: Bot):
    req_id=int(call.data.replace("acc_req_",""))
    req=db.get_request(req_id)
    if not req: await call.answer("So'rov topilmadi!",show_alert=True); return
    team=db.get_team(req["team_id"])
    if team["leader_id"]!=call.from_user.id: await call.answer("Faqat lider!",show_alert=True); return
    ok,msg=db.accept_request(req_id)
    if not ok: await call.answer({"full":"Jamoa to'liq!","duplicate":"Allaqachon a'zo!"}.get(msg,msg),show_alert=True); return
    await call.message.edit_text(f"✅ <b>{req['mlbb_nick'] or req['username']}</b> qo'shildi!\n📍 {req['lane']}",parse_mode="HTML")
    # Guruh chatiga ham qo'sh
    try:
        await bot.send_message(req["user_id"],
            f"🎉 <b>Qabul qilindi!</b>\n\n👥 <b>{team['team_name']}</b>\n📍 {req['lane']}\n\n"
            f"Jamoa guruhiga qo'shilish uchun /chat_{team['id']} buyrug'ini yuboring!",
            parse_mode="HTML")
    except: pass

@router.callback_query(F.data.startswith("rej_req_"))
async def reject_req(call: CallbackQuery, bot: Bot):
    req_id=int(call.data.replace("rej_req_",""))
    req=db.get_request(req_id)
    if not req: return
    team=db.get_team(req["team_id"])
    if team["leader_id"]!=call.from_user.id: await call.answer("Faqat lider!"); return
    db.reject_request(req_id)
    await call.message.edit_text(f"❌ <b>{req['mlbb_nick'] or req['username']}</b> rad etildi.",parse_mode="HTML")
    try: await bot.send_message(req["user_id"],f"❌ <b>{team['team_name']}</b> so'rovingizni rad etdi.\nBoshqa jamoa qidiring.",parse_mode="HTML")
    except: pass

# ── JAMOA BOSHQARUVI ─────────────────────────────────────────────────

@router.callback_query(F.data.startswith("myteam_"))
async def my_team(call: CallbackQuery):
    tid=int(call.data.split("_")[1])
    team=db.get_user_team(call.from_user.id,tid)
    if not team: await call.answer("Jamoangiz topilmadi!",show_alert=True); return
    players=db.get_team_players(team["id"])
    pending_reqs=db.get_pending_requests(team["id"])
    is_leader=team["leader_id"]==call.from_user.id
    text=(f"👥 <b>{team['team_name']}</b>\n🏫 {team.get('school','—')}\n"
          f"✅ G'alaba: {team['wins']} | ❌ Mag'lubiyat: {team['losses']}\n"
          f"Check-in: {'✅' if team.get('checked_in') else '❌'}\n\n<b>Tarkib:</b>\n")
    for p in players:
        tag="👑" if p["is_leader"] else "•"
        mvp=" ⭐" if p.get("is_mvp") else ""
        text+=f"{tag} {p.get('mlbb_nick') or p['username']} — {p['lane']}{mvp}\n"
    if pending_reqs and is_leader:
        text+=f"\n📨 <b>{len(pending_reqs)} ta kutilayotgan so'rov!</b>"
    btns=[]
    if is_leader:
        btns.append([InlineKeyboardButton(text="⚙️ Boshqaruv",callback_data=f"manage_team_{team['id']}")])
        if pending_reqs:
            btns.append([InlineKeyboardButton(text=f"📨 So'rovlar ({len(pending_reqs)})",callback_data=f"view_reqs_{team['id']}")])
    else:
        btns.append([InlineKeyboardButton(text="🚪 Chiqish",callback_data=f"leave_{team['id']}")])
    await call.message.answer(text,reply_markup=InlineKeyboardMarkup(inline_keyboard=btns),parse_mode="HTML")

@router.callback_query(F.data.startswith("manage_team_"))
async def manage_team(call: CallbackQuery):
    team_id=int(call.data.replace("manage_team_",""))
    team=db.get_team(team_id)
    if team["leader_id"]!=call.from_user.id: await call.answer("Faqat lider!"); return
    players=db.get_team_players(team_id)
    t=db.get_tournament(team["tournament_id"])
    btns=[]
    for p in players:
        if not p["is_leader"]:
            btns.append([
                InlineKeyboardButton(text=f"🚫 {p.get('mlbb_nick') or p['username']}",callback_data=f"kick_{team_id}_{p['user_id']}"),
                InlineKeyboardButton(text="👑 Lider",callback_data=f"transfer_{team_id}_{p['user_id']}"),
            ])
    if t["status"]=="reg":
        btns.append([InlineKeyboardButton(text="🗑 Jamoani tarqatish",callback_data=f"disband_{team_id}")])
    await call.message.answer(
        f"⚙️ <b>{team['team_name']} — Boshqaruv</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns),parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("view_reqs_"))
async def view_reqs(call: CallbackQuery):
    team_id=int(call.data.replace("view_reqs_",""))
    team=db.get_team(team_id)
    if team["leader_id"]!=call.from_user.id: return
    reqs=db.get_pending_requests(team_id)
    if not reqs: await call.answer("So'rovlar yo'q!"); return
    for req in reqs:
        await call.message.answer(
            f"📨 <b>So'rov</b>\n\n👤 {req.get('mlbb_nick') or req['username']}\n"
            f"🆔 {req['mlbb_id']}\n🏅 {req.get('rank','—')}\n📍 {req['lane']}\n🏫 {req.get('school','—')}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="✅ Qabul",callback_data=f"acc_req_{req['id']}"),
                InlineKeyboardButton(text="❌ Rad",callback_data=f"rej_req_{req['id']}"),
            ]]),parse_mode="HTML"
        )

@router.callback_query(F.data.startswith("kick_"))
async def kick(call: CallbackQuery, bot: Bot):
    parts=call.data.split("_"); team_id,uid=int(parts[1]),int(parts[2])
    team=db.get_team(team_id)
    if team["leader_id"]!=call.from_user.id: return
    db.kick_player(team_id,uid)
    await call.answer("✅ Chiqarildi!"); await call.message.edit_text("✅ O'yinchi chiqarildi.")
    try: await bot.send_message(uid,f"❌ <b>{team['team_name']}</b> jamoasidan chiqarildingiz.",parse_mode="HTML")
    except: pass

@router.callback_query(F.data.startswith("transfer_"))
async def transfer(call: CallbackQuery, bot: Bot):
    parts=call.data.split("_"); team_id,uid=int(parts[1]),int(parts[2])
    team=db.get_team(team_id)
    if team["leader_id"]!=call.from_user.id: return
    db.transfer_leadership(team_id,uid)
    await call.message.edit_text("✅ Liderlik berildi!")
    try: await bot.send_message(uid,f"👑 Siz <b>{team['team_name']}</b> jamoasining yangi lideri bo'ldingiz!",parse_mode="HTML")
    except: pass

@router.callback_query(F.data.startswith("disband_"))
async def disband(call: CallbackQuery):
    team_id=int(call.data.replace("disband_",""))
    team=db.get_team(team_id)
    t=db.get_tournament(team["tournament_id"])
    if t["status"]!="reg": await call.answer("Turnir boshlangan!",show_alert=True); return
    db.disband_team(team_id)
    await call.message.edit_text(f"✅ <b>{team['team_name']}</b> tarqatildi.",parse_mode="HTML")

@router.callback_query(F.data.startswith("leave_"))
async def leave(call: CallbackQuery):
    team_id=int(call.data.replace("leave_",""))
    team=db.get_team(team_id)
    t=db.get_tournament(team["tournament_id"])
    if t["status"]!="reg": await call.answer("Turnir boshlangan!",show_alert=True); return
    db.remove_player(team_id,call.from_user.id)
    await call.message.edit_text("✅ Jamoadan chiqdingiz!")

@router.callback_query(F.data == "cancel_reg")
async def cancel_reg(call: CallbackQuery):
    db.clear_state(call.from_user.id); await call.message.delete()

# ── O'YINCHI → ADMIN XABAR ────────────────────────────────────────────

@router.callback_query(F.data == "contact_admin")
async def contact_admin(call: CallbackQuery):
    db.set_state(call.from_user.id,"support_msg",{})
    await call.message.answer(
        "📨 <b>Adminga xabar</b>\n\n"
        "Xabaringizni yuboring.\n"
        "Rasm yoki GIF ham yuborishingiz mumkin!",
        parse_mode="HTML"
    )
