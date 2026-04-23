import sqlite3, json
from datetime import datetime

DB_FILE = "esports.db"

def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn(); c = conn.cursor()

    c.execute("CREATE TABLE IF NOT EXISTS bot_settings (key TEXT PRIMARY KEY, value TEXT)")
    c.execute("INSERT OR IGNORE INTO bot_settings VALUES ('channels','[]')")

    # Foydalanuvchilar
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT, first_name TEXT,
        mlbb_id TEXT, mlbb_nick TEXT, rank TEXT,
        school TEXT,
        total_wins INTEGER DEFAULT 0,
        total_losses INTEGER DEFAULT 0,
        total_mvp INTEGER DEFAULT 0,
        tournaments_played INTEGER DEFAULT 0,
        registered_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # Turnirlar
    c.execute('''CREATE TABLE IF NOT EXISTS tournaments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT, description TEXT,
        prize_pool TEXT, prize_distribution TEXT,
        format TEXT DEFAULT 'single',
        max_teams INTEGER DEFAULT 16,
        team_size INTEGER DEFAULT 5,
        status TEXT DEFAULT 'draft',
        reg_deadline TEXT,
        offline_location TEXT, offline_date TEXT,
        rules TEXT,
        banner_file_id TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        created_by INTEGER
    )''')

    # Jamoalar
    c.execute('''CREATE TABLE IF NOT EXISTS teams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tournament_id INTEGER,
        team_name TEXT,
        school TEXT,
        leader_id INTEGER, leader_username TEXT,
        status TEXT DEFAULT 'pending',
        wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0,
        points INTEGER DEFAULT 0,
        checked_in INTEGER DEFAULT 0,
        chat_id INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # O'yinchilar
    c.execute('''CREATE TABLE IF NOT EXISTS players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        team_id INTEGER,
        user_id INTEGER,
        username TEXT,
        mlbb_id TEXT, mlbb_nick TEXT,
        lane TEXT, rank TEXT, school TEXT,
        is_leader INTEGER DEFAULT 0,
        is_mvp INTEGER DEFAULT 0,
        joined_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # Qo'shilish so'rovlari
    c.execute('''CREATE TABLE IF NOT EXISTS join_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        team_id INTEGER,
        user_id INTEGER, username TEXT,
        mlbb_id TEXT, mlbb_nick TEXT,
        lane TEXT, rank TEXT, school TEXT,
        status TEXT DEFAULT 'pending',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # Matchlar
    c.execute('''CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tournament_id INTEGER,
        round_number INTEGER DEFAULT 1,
        round_name TEXT DEFAULT '',
        team1_id INTEGER, team2_id INTEGER,
        winner_id INTEGER, loser_id INTEGER,
        result_type TEXT DEFAULT '',
        mvp_user_id INTEGER,
        lobby_id TEXT, lobby_password TEXT,
        status TEXT DEFAULT 'pending',
        screenshot_file_id TEXT,
        scheduled_at TEXT, played_at TEXT
    )''')

    # Screenshots
    c.execute('''CREATE TABLE IF NOT EXISTS pending_screenshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        match_id INTEGER, team_id INTEGER,
        user_id INTEGER, file_id TEXT,
        claimed_winner INTEGER,
        submitted_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # O'yinchi — Admin xabarlar
    c.execute('''CREATE TABLE IF NOT EXISTS support_tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, username TEXT,
        message TEXT, file_id TEXT, file_type TEXT,
        admin_reply TEXT,
        status TEXT DEFAULT 'open',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # User states
    c.execute("CREATE TABLE IF NOT EXISTS user_states (user_id INTEGER PRIMARY KEY, state TEXT, data TEXT DEFAULT '{}')")

    conn.commit(); conn.close()
    print("✅ DB tayyor!")

# ── SOZLAMALAR ────────────────────────────────────────────────────────

def get_setting(key):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT value FROM bot_settings WHERE key=?", (key,))
    row = c.fetchone(); conn.close()
    return json.loads(row["value"]) if row else []

def set_setting(key, val):
    conn = get_conn(); c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO bot_settings VALUES (?,?)", (key, json.dumps(val, ensure_ascii=False)))
    conn.commit(); conn.close()

def get_channels(): return get_setting("channels")
def save_channels(v): set_setting("channels", v)
def add_channel(cid, name, link=""):
    chs = get_channels()
    if any(c["id"]==cid for c in chs): return False
    chs.append({"id":cid,"name":name,"link":link}); save_channels(chs); return True
def remove_channel(cid): save_channels([c for c in get_channels() if c["id"]!=cid])

# ── FOYDALANUVCHILAR ──────────────────────────────────────────────────

def register_user(uid, username, first_name):
    conn = get_conn(); c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id,username,first_name) VALUES (?,?,?)", (uid,username,first_name))
    c.execute("UPDATE users SET username=?,first_name=? WHERE user_id=?", (username,first_name,uid))
    conn.commit(); conn.close()

def get_user(uid):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    row = c.fetchone(); conn.close()
    return dict(row) if row else None

def update_user_profile(uid, mlbb_id, mlbb_nick, rank, school=""):
    conn = get_conn(); c = conn.cursor()
    c.execute("UPDATE users SET mlbb_id=?,mlbb_nick=?,rank=?,school=? WHERE user_id=?", (mlbb_id,mlbb_nick,rank,school,uid))
    conn.commit(); conn.close()

def get_all_users():
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM users"); rows = c.fetchall(); conn.close()
    return [dict(r) for r in rows]

# ── TURNIRLAR ─────────────────────────────────────────────────────────

def create_tournament(data, created_by):
    conn = get_conn(); c = conn.cursor()
    c.execute('''INSERT INTO tournaments
        (title,description,prize_pool,prize_distribution,format,max_teams,team_size,reg_deadline,rules,created_by)
        VALUES (?,?,?,?,?,?,?,?,?,?)''',
        (data.get("title"),data.get("description",""),data.get("prize_pool",""),
         data.get("prize_distribution",""),data.get("format","single"),
         data.get("max_teams",16),data.get("team_size",5),
         data.get("deadline_iso",""),data.get("rules",""),created_by))
    tid = c.lastrowid; conn.commit(); conn.close(); return tid

def get_tournament(tid):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM tournaments WHERE id=?", (tid,))
    row = c.fetchone(); conn.close()
    return dict(row) if row else None

def get_active_tournaments():
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM tournaments WHERE status IN ('reg','checkin','online','offline') ORDER BY id DESC")
    rows = c.fetchall(); conn.close(); return [dict(r) for r in rows]

def get_all_tournaments():
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM tournaments ORDER BY id DESC")
    rows = c.fetchall(); conn.close(); return [dict(r) for r in rows]

def update_tournament(tid, **kw):
    conn = get_conn(); c = conn.cursor()
    for k,v in kw.items(): c.execute(f"UPDATE tournaments SET {k}=? WHERE id=?", (v,tid))
    conn.commit(); conn.close()

def set_tournament_banner(tid, file_id):
    update_tournament(tid, banner_file_id=file_id)

# ── JAMOALAR ─────────────────────────────────────────────────────────

def create_team(tournament_id, team_name, school, leader_id, leader_username):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM players WHERE user_id=? AND team_id IN (SELECT id FROM teams WHERE tournament_id=?)",
              (leader_id,tournament_id))
    if c.fetchone(): conn.close(); return None,"already"
    c.execute("INSERT INTO teams (tournament_id,team_name,school,leader_id,leader_username) VALUES (?,?,?,?,?)",
              (tournament_id,team_name,school,leader_id,leader_username))
    tid = c.lastrowid; conn.commit(); conn.close(); return tid,"ok"

def get_team(tid):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM teams WHERE id=?", (tid,))
    row = c.fetchone(); conn.close(); return dict(row) if row else None

def get_team_players(tid):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM players WHERE team_id=? ORDER BY is_leader DESC", (tid,))
    rows = c.fetchall(); conn.close(); return [dict(r) for r in rows]

def get_teams_by_tournament(tid):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM teams WHERE tournament_id=? ORDER BY points DESC,wins DESC", (tid,))
    rows = c.fetchall(); conn.close(); return [dict(r) for r in rows]

def get_user_team(uid, tournament_id):
    conn = get_conn(); c = conn.cursor()
    c.execute('''SELECT t.* FROM teams t JOIN players p ON p.team_id=t.id
                 WHERE p.user_id=? AND t.tournament_id=?''', (uid,tournament_id))
    row = c.fetchone(); conn.close(); return dict(row) if row else None

def get_team_missing_lanes(team_id):
    from config import MLBB_LANES
    players = get_team_players(team_id)
    filled = [p["lane"] for p in players]
    return [l for l in MLBB_LANES if l not in filled]

def add_player_direct(team_id, uid, username, mlbb_id, mlbb_nick, lane, rank, school, is_leader=0):
    conn = get_conn(); c = conn.cursor()
    team = get_team(team_id)
    t = get_tournament(team["tournament_id"]) if team else None
    max_size = t["team_size"] if t else 5
    c.execute("SELECT COUNT(*) as n FROM players WHERE team_id=?", (team_id,))
    if c.fetchone()["n"] >= max_size: conn.close(); return False,"full"
    c.execute("SELECT * FROM players WHERE user_id=? AND team_id=?", (uid,team_id))
    if c.fetchone(): conn.close(); return False,"duplicate"
    c.execute("INSERT INTO players (team_id,user_id,username,mlbb_id,mlbb_nick,lane,rank,school,is_leader) VALUES (?,?,?,?,?,?,?,?,?)",
              (team_id,uid,username,mlbb_id,mlbb_nick,lane,rank,school,is_leader))
    c.execute("SELECT COUNT(*) as n FROM players WHERE team_id=?", (team_id,))
    if c.fetchone()["n"] >= max_size:
        c.execute("UPDATE teams SET status='complete' WHERE id=?", (team_id,))
    conn.commit(); conn.close(); return True,"ok"

def remove_player(team_id, uid):
    conn = get_conn(); c = conn.cursor()
    c.execute("DELETE FROM players WHERE team_id=? AND user_id=? AND is_leader=0", (team_id,uid))
    c.execute("UPDATE teams SET status='pending' WHERE id=?", (team_id,))
    conn.commit(); conn.close()

def kick_player(team_id, uid):
    return remove_player(team_id, uid)

def disband_team(team_id):
    conn = get_conn(); c = conn.cursor()
    c.execute("DELETE FROM players WHERE team_id=?", (team_id,))
    c.execute("DELETE FROM teams WHERE id=?", (team_id,))
    conn.commit(); conn.close()

def transfer_leadership(team_id, new_uid):
    conn = get_conn(); c = conn.cursor()
    c.execute("UPDATE players SET is_leader=0 WHERE team_id=?", (team_id,))
    c.execute("UPDATE players SET is_leader=1 WHERE team_id=? AND user_id=?", (team_id,new_uid))
    c.execute("SELECT username FROM players WHERE team_id=? AND user_id=?", (team_id,new_uid))
    row = c.fetchone()
    if row: c.execute("UPDATE teams SET leader_id=?,leader_username=? WHERE id=?", (new_uid,row["username"],team_id))
    conn.commit(); conn.close()

def checkin_team(team_id):
    conn = get_conn(); c = conn.cursor()
    c.execute("UPDATE teams SET checked_in=1,status='checked_in' WHERE id=?", (team_id,))
    conn.commit(); conn.close()

def update_team_result(team_id, won):
    conn = get_conn(); c = conn.cursor()
    if won: c.execute("UPDATE teams SET wins=wins+1,points=points+3 WHERE id=?", (team_id,))
    else: c.execute("UPDATE teams SET losses=losses+1,status='eliminated' WHERE id=?", (team_id,))
    conn.commit(); conn.close()

def save_team_chat(team_id, chat_id):
    conn = get_conn(); c = conn.cursor()
    c.execute("UPDATE teams SET chat_id=? WHERE id=?", (chat_id,team_id))
    conn.commit(); conn.close()

# ── QO'SHILISH SO'ROVLARI ─────────────────────────────────────────────

def create_join_request(team_id, uid, username, mlbb_id, mlbb_nick, lane, rank, school):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM join_requests WHERE team_id=? AND user_id=? AND status='pending'", (team_id,uid))
    if c.fetchone(): conn.close(); return None,"already_requested"
    c.execute("INSERT INTO join_requests (team_id,user_id,username,mlbb_id,mlbb_nick,lane,rank,school) VALUES (?,?,?,?,?,?,?,?)",
              (team_id,uid,username,mlbb_id,mlbb_nick,lane,rank,school))
    rid = c.lastrowid; conn.commit(); conn.close(); return rid,"ok"

def get_pending_requests(team_id):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM join_requests WHERE team_id=? AND status='pending' ORDER BY created_at", (team_id,))
    rows = c.fetchall(); conn.close(); return [dict(r) for r in rows]

def get_request(req_id):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM join_requests WHERE id=?", (req_id,))
    row = c.fetchone(); conn.close(); return dict(row) if row else None

def accept_request(req_id):
    req = get_request(req_id)
    if not req: return False,"not_found"
    ok, msg = add_player_direct(req["team_id"],req["user_id"],req["username"],
        req["mlbb_id"],req["mlbb_nick"],req["lane"],req["rank"],req["school"])
    if ok:
        conn = get_conn(); c = conn.cursor()
        c.execute("UPDATE join_requests SET status='accepted' WHERE id=?", (req_id,))
        conn.commit(); conn.close()
    return ok, msg

def reject_request(req_id):
    conn = get_conn(); c = conn.cursor()
    c.execute("UPDATE join_requests SET status='rejected' WHERE id=?", (req_id,))
    conn.commit(); conn.close()

def get_user_pending_request(uid, tournament_id):
    conn = get_conn(); c = conn.cursor()
    c.execute('''SELECT jr.* FROM join_requests jr JOIN teams t ON t.id=jr.team_id
                 WHERE jr.user_id=? AND t.tournament_id=? AND jr.status='pending' ''', (uid,tournament_id))
    row = c.fetchone(); conn.close(); return dict(row) if row else None

# ── MATCHLAR ─────────────────────────────────────────────────────────

def create_match(tournament_id, round_number, team1_id, team2_id, round_name="", scheduled_at=None):
    conn = get_conn(); c = conn.cursor()
    c.execute("INSERT INTO matches (tournament_id,round_number,round_name,team1_id,team2_id,scheduled_at) VALUES (?,?,?,?,?,?)",
              (tournament_id,round_number,round_name,team1_id,team2_id,scheduled_at))
    mid = c.lastrowid; conn.commit(); conn.close(); return mid

def set_lobby(match_id, lobby_id, password=""):
    conn = get_conn(); c = conn.cursor()
    c.execute("UPDATE matches SET lobby_id=?,lobby_password=?,status='lobby_sent' WHERE id=?", (lobby_id,password,match_id))
    conn.commit(); conn.close()

def submit_result(match_id, winner_id, loser_id, result_type="win", mvp_user_id=None):
    conn = get_conn(); c = conn.cursor()
    c.execute("UPDATE matches SET winner_id=?,loser_id=?,result_type=?,mvp_user_id=?,status='finished',played_at=? WHERE id=?",
              (winner_id,loser_id,result_type,mvp_user_id,datetime.now().isoformat(),match_id))
    conn.commit(); conn.close()
    update_team_result(winner_id, True)
    update_team_result(loser_id, False)
    # Stats
    for p in get_team_players(winner_id):
        conn2=get_conn(); c2=conn2.cursor()
        c2.execute("UPDATE users SET total_wins=total_wins+1,tournaments_played=tournaments_played+1 WHERE user_id=?", (p["user_id"],))
        conn2.commit(); conn2.close()
    for p in get_team_players(loser_id):
        conn2=get_conn(); c2=conn2.cursor()
        c2.execute("UPDATE users SET total_losses=total_losses+1,tournaments_played=tournaments_played+1 WHERE user_id=?", (p["user_id"],))
        conn2.commit(); conn2.close()
    if mvp_user_id:
        conn2=get_conn(); c2=conn2.cursor()
        c2.execute("UPDATE users SET total_mvp=total_mvp+1 WHERE user_id=?", (mvp_user_id,))
        conn2.commit(); conn2.close()

def get_match(mid):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM matches WHERE id=?", (mid,))
    row = c.fetchone(); conn.close(); return dict(row) if row else None

def get_pending_matches(tournament_id):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM matches WHERE tournament_id=? AND status IN ('pending','lobby_sent') ORDER BY round_number,id", (tournament_id,))
    rows = c.fetchall(); conn.close(); return [dict(r) for r in rows]

def get_finished_matches(tournament_id):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM matches WHERE tournament_id=? AND status='finished' ORDER BY round_number,id", (tournament_id,))
    rows = c.fetchall(); conn.close(); return [dict(r) for r in rows]

def get_all_matches(tournament_id):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM matches WHERE tournament_id=? ORDER BY round_number,id", (tournament_id,))
    rows = c.fetchall(); conn.close(); return [dict(r) for r in rows]

# ── SCREENSHOT ────────────────────────────────────────────────────────

def submit_screenshot(match_id, team_id, uid, file_id, claimed_winner):
    conn = get_conn(); c = conn.cursor()
    c.execute("DELETE FROM pending_screenshots WHERE match_id=? AND team_id=?", (match_id,team_id))
    c.execute("INSERT INTO pending_screenshots (match_id,team_id,user_id,file_id,claimed_winner) VALUES (?,?,?,?,?)",
              (match_id,team_id,uid,file_id,claimed_winner))
    c.execute("UPDATE matches SET screenshot_file_id=? WHERE id=?", (file_id,match_id))
    conn.commit(); conn.close()

def get_pending_screenshots():
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM pending_screenshots ORDER BY submitted_at DESC")
    rows = c.fetchall(); conn.close(); return [dict(r) for r in rows]

def confirm_screenshot(sc_id):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM pending_screenshots WHERE id=?", (sc_id,))
    row = c.fetchone()
    if row: c.execute("DELETE FROM pending_screenshots WHERE id=?", (sc_id,))
    conn.commit(); conn.close(); return dict(row) if row else None

def delete_screenshot(sc_id):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM pending_screenshots WHERE id=?", (sc_id,))
    row = c.fetchone()
    if row: c.execute("DELETE FROM pending_screenshots WHERE id=?", (sc_id,))
    conn.commit(); conn.close(); return dict(row) if row else None

def set_mvp(match_id, uid):
    conn = get_conn(); c = conn.cursor()
    c.execute("UPDATE matches SET mvp_user_id=? WHERE id=?", (uid,match_id))
    conn.commit(); conn.close()

# ── SUPPORT / XABARLAR ────────────────────────────────────────────────

def create_ticket(uid, username, message, file_id=None, file_type=None):
    conn = get_conn(); c = conn.cursor()
    c.execute("INSERT INTO support_tickets (user_id,username,message,file_id,file_type) VALUES (?,?,?,?,?)",
              (uid,username,message,file_id,file_type))
    tid = c.lastrowid; conn.commit(); conn.close(); return tid

def get_open_tickets():
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM support_tickets WHERE status='open' ORDER BY created_at DESC")
    rows = c.fetchall(); conn.close(); return [dict(r) for r in rows]

def get_ticket(tid):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM support_tickets WHERE id=?", (tid,))
    row = c.fetchone(); conn.close(); return dict(row) if row else None

def close_ticket(tid, reply=""):
    conn = get_conn(); c = conn.cursor()
    c.execute("UPDATE support_tickets SET status='closed',admin_reply=? WHERE id=?", (reply,tid))
    conn.commit(); conn.close()

# ── USER STATE ────────────────────────────────────────────────────────

def set_state(uid, state, data=None):
    conn = get_conn(); c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO user_states VALUES (?,?,?)",
              (uid,state,json.dumps(data or {},ensure_ascii=False)))
    conn.commit(); conn.close()

def get_state(uid):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM user_states WHERE user_id=?", (uid,))
    row = c.fetchone(); conn.close()
    return (row["state"],json.loads(row["data"])) if row else (None,{})

def clear_state(uid):
    conn = get_conn(); c = conn.cursor()
    c.execute("DELETE FROM user_states WHERE user_id=?", (uid,))
    conn.commit(); conn.close()
