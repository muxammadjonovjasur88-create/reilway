"""
Eslatma va auto-deadline scheduler
APScheduler kutubxonasiz oddiy asyncio bilan ishlaydi
"""
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot
import database as db

async def check_deadlines(bot: Bot):
    """Har 60 soniyada deadline va match eslatmalarini tekshiradi"""
    while True:
        try:
            await _check_reg_deadlines(bot)
            await _check_match_reminders(bot)
        except Exception as e:
            print(f"Scheduler xato: {e}")
        await asyncio.sleep(60)

async def _check_reg_deadlines(bot: Bot):
    """Ro'yxatdan o'tish muddati tugagan turnirlarni yopadi"""
    conn = db.get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM tournaments WHERE status='reg' AND reg_deadline IS NOT NULL AND reg_deadline != ''")
    tournaments = [dict(r) for r in c.fetchall()]
    conn.close()

    now = datetime.now()
    for t in tournaments:
        try:
            # Deadline formatini parse qilish (ISO format)
            deadline = datetime.fromisoformat(t["reg_deadline"])
            
            # 30 daqiqa qolganida eslatma
            if timedelta(minutes=0) < (deadline - now) <= timedelta(minutes=30):
                await _notify_deadline_soon(bot, t)
            
            # Muddati tugagan
            if now >= deadline:
                db.update_tournament_status(t["id"], "online")
                await _notify_deadline_passed(bot, t)
        except:
            pass

async def _notify_deadline_soon(bot: Bot, tournament):
    """30 daqiqa qolganida barcha ro'yxatdagi o'yinchilarga eslatma"""
    teams = db.get_teams_by_tournament(tournament["id"])
    notified = set()
    for team in teams:
        players = db.get_team_players(team["id"])
        for p in players:
            if p["user_id"] not in notified:
                try:
                    await bot.send_message(
                        p["user_id"],
                        f"⏰ <b>Eslatma!</b>\n\n"
                        f"🏆 <b>{tournament['title']}</b> turnirida\n"
                        f"Ro'yxatdan o'tishga <b>30 daqiqa</b> qoldi!\n\n"
                        f"Jamoangizni to'ldiring!",
                        parse_mode="HTML"
                    )
                    notified.add(p["user_id"])
                except:
                    pass

async def _notify_deadline_passed(bot: Bot, tournament):
    """Muddati tugaganda barcha o'yinchilarga xabar"""
    teams = db.get_teams_by_tournament(tournament["id"])
    notified = set()
    for team in teams:
        players = db.get_team_players(team["id"])
        for p in players:
            if p["user_id"] not in notified:
                try:
                    await bot.send_message(
                        p["user_id"],
                        f"🔒 <b>{tournament['title']}</b>\n\n"
                        f"Ro'yxatdan o'tish muddati tugadi!\n"
                        f"Tez orada matchlar e'lon qilinadi. ⚔️",
                        parse_mode="HTML"
                    )
                    notified.add(p["user_id"])
                except:
                    pass

async def _check_match_reminders(bot: Bot):
    """Match vaqtidan 15 daqiqa oldin eslatma"""
    conn = db.get_conn()
    c = conn.cursor()
    c.execute("""SELECT * FROM matches 
                 WHERE status='lobby_sent' 
                 AND scheduled_at IS NOT NULL 
                 AND scheduled_at != ''""")
    matches = [dict(r) for r in c.fetchall()]
    conn.close()

    now = datetime.now()
    for m in matches:
        try:
            scheduled = datetime.fromisoformat(m["scheduled_at"])
            diff = scheduled - now
            # 15 daqiqa qolsa eslatma yuboramiz (faqat bir marta)
            if timedelta(minutes=14) <= diff <= timedelta(minutes=15):
                await _send_match_reminder(bot, m)
        except:
            pass

async def _send_match_reminder(bot: Bot, match):
    """Ikkala jamoaga match eslatmasi"""
    t1 = db.get_team(match["team1_id"])
    t2 = db.get_team(match["team2_id"])
    if not t1 or not t2:
        return

    for team in [t1, t2]:
        players = db.get_team_players(team["id"])
        for p in players:
            try:
                await bot.send_message(
                    p["user_id"],
                    f"⏰ <b>Match eslatmasi!</b>\n\n"
                    f"⚔️ <b>{t1['team_name']}</b> vs <b>{t2['team_name']}</b>\n"
                    f"🕐 <b>15 daqiqadan keyin!</b>\n\n"
                    f"🎮 Lobby ID: <code>{match.get('lobby_id', 'kutilmoqda')}</code>\n\n"
                    f"Tayyor bo'ling! 💪",
                    parse_mode="HTML"
                )
            except:
                pass

async def send_match_notification(bot: Bot, match_id: int):
    """Match lobby berilganda darhol xabar yuborish"""
    match = db.get_match(match_id)
    if not match:
        return
    t1 = db.get_team(match["team1_id"])
    t2 = db.get_team(match["team2_id"])

    for team in [t1, t2]:
        players = db.get_team_players(team["id"])
        for p in players:
            try:
                await bot.send_message(
                    p["user_id"],
                    f"🎮 <b>Match tayyor!</b>\n\n"
                    f"⚔️ <b>{t1['team_name']}</b> vs <b>{t2['team_name']}</b>\n\n"
                    f"🔑 Lobby ID: <code>{match['lobby_id']}</code>\n\n"
                    f"O'yinga kiring va boshlang! 🏆",
                    parse_mode="HTML"
                )
            except:
                pass
