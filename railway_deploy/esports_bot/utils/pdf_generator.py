from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_CENTER
import database as db, tempfile
from datetime import datetime

def generate_teams_pdf(tournament_id):
    t = db.get_tournament(tournament_id)
    teams = db.get_teams_by_tournament(tournament_id)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    doc = SimpleDocTemplate(tmp.name, pagesize=A4,
                            rightMargin=1.5*cm, leftMargin=1.5*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    title_s = ParagraphStyle("t", parent=styles["Title"], fontSize=16, alignment=TA_CENTER, textColor=colors.HexColor("#1a1a2e"), spaceAfter=4)
    sub_s   = ParagraphStyle("s", parent=styles["Normal"], fontSize=10, alignment=TA_CENTER, textColor=colors.grey, spaceAfter=4)
    sec_s   = ParagraphStyle("sec", parent=styles["Heading2"], fontSize=12, textColor=colors.HexColor("#16213e"), spaceBefore=10, spaceAfter=3)
    elements = []
    elements.append(Paragraph(t['title'], title_s))
    elements.append(Paragraph(f"Jamoalar Royxati | {datetime.now().strftime('%d.%m.%Y %H:%M')}", sub_s))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#e94560")))
    elements.append(Spacer(1, 0.3*cm))

    info = [["Format:", t.get("format","—"), "Jamoalar:", f"{len(teams)}/{t['max_teams']}"],
            ["Sovrin:", t.get("prize_pool","—"), "Holat:", t.get("status","—")]]
    it = Table(info, colWidths=[3.5*cm,5*cm,3.5*cm,5*cm])
    it.setStyle(TableStyle([
        ("FONTSIZE",(0,0),(-1,-1),9),
        ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),("FONTNAME",(2,0),(2,-1),"Helvetica-Bold"),
        ("TEXTCOLOR",(0,0),(0,-1),colors.HexColor("#e94560")),
        ("TEXTCOLOR",(2,0),(2,-1),colors.HexColor("#e94560")),
        ("BOTTOMPADDING",(0,0),(-1,-1),3),
    ]))
    elements.append(it); elements.append(Spacer(1, 0.4*cm))

    for i, team in enumerate(teams, 1):
        players = db.get_team_players(team["id"])
        st = {"pending":"Kutilmoqda","complete":"Tayyor","checked_in":"Check-in","eliminated":"Eliminated","winner":"G'olib"}.get(team["status"],"—")
        elements.append(Paragraph(f"{i}. {team['team_name']}  [{st}]  |  Maktab: {team.get('school','—')}  |  W:{team['wins']} L:{team['losses']}", sec_s))
        if players:
            header = [["#","Nick","MLBB ID","Liniya","Rank","Maktab"]]
            rows = []
            for j,p in enumerate(players,1):
                lmark = "LIDER " if p["is_leader"] else ""
                rows.append([str(j), f"{lmark}{p.get('mlbb_nick') or p['username']}",
                             p.get("mlbb_id","—"), p.get("lane","—"), p.get("rank","—"), p.get("school","—")])
            tbl = Table(header+rows, colWidths=[0.8*cm,4*cm,3*cm,3.5*cm,3*cm,3*cm])
            tbl.setStyle(TableStyle([
                ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#16213e")),
                ("TEXTCOLOR",(0,0),(-1,0),colors.white),
                ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
                ("FONTSIZE",(0,0),(-1,-1),8),
                ("ALIGN",(0,0),(-1,-1),"CENTER"),
                ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.HexColor("#f0f4f8"),colors.white]),
                ("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#ccc")),
                ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3),
            ]))
            elements.append(tbl)
        elements.append(Spacer(1,0.2*cm))

    doc.build(elements)
    return tmp.name

def generate_matches_pdf(tournament_id):
    t = db.get_tournament(tournament_id)
    all_matches = db.get_all_matches(tournament_id)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    doc = SimpleDocTemplate(tmp.name, pagesize=A4,
                            rightMargin=1.5*cm, leftMargin=1.5*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    title_s = ParagraphStyle("t", parent=styles["Title"], fontSize=16, alignment=TA_CENTER, textColor=colors.HexColor("#1a1a2e"))
    sub_s   = ParagraphStyle("s", parent=styles["Normal"], fontSize=10, alignment=TA_CENTER, textColor=colors.grey, spaceAfter=6)
    round_s = ParagraphStyle("r", parent=styles["Heading2"], fontSize=12, textColor=colors.HexColor("#e94560"), spaceBefore=8, spaceAfter=3)
    elements = []
    elements.append(Paragraph(f"{t['title']} — Match Jadvali", title_s))
    elements.append(Paragraph(f"{datetime.now().strftime('%d.%m.%Y %H:%M')}", sub_s))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#e94560")))
    elements.append(Spacer(1, 0.4*cm))

    rounds = {}
    for m in all_matches:
        rn = m.get("round_name") or f"Round {m['round_number']}"
        rounds.setdefault(rn, []).append(m)

    for rname, matches in rounds.items():
        elements.append(Paragraph(f"  {rname}", round_s))
        header = [["#","Jamoa 1","vs","Jamoa 2","Lobby","G'olib","Holat"]]
        rows = []
        for i,m in enumerate(matches,1):
            t1 = db.get_team(m["team1_id"]); t2 = db.get_team(m["team2_id"])
            w = db.get_team(m["winner_id"]) if m["winner_id"] else None
            st = {"pending":"Kutilmoqda","lobby_sent":"Lobby berildi","finished":"Tugadi"}.get(m["status"],"—")
            rows.append([str(i), t1["team_name"] if t1 else "—", "vs",
                         t2["team_name"] if t2 else "—",
                         m.get("lobby_id","—") or "—",
                         w["team_name"] if w else "—", st])
        tbl = Table(header+rows, colWidths=[0.7*cm,4*cm,0.7*cm,4*cm,2.2*cm,3.5*cm,2.4*cm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#16213e")),
            ("TEXTCOLOR",(0,0),(-1,0),colors.white),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
            ("FONTSIZE",(0,0),(-1,-1),8),("ALIGN",(0,0),(-1,-1),"CENTER"),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.HexColor("#f0f4f8"),colors.white]),
            ("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#ccc")),
            ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
        ]))
        elements.append(tbl); elements.append(Spacer(1,0.3*cm))

    finished = len([m for m in all_matches if m["status"]=="finished"])
    elements.append(HRFlowable(width="100%",thickness=1,color=colors.grey))
    elements.append(Paragraph(f"Jami {len(all_matches)} match | Tugagan: {finished} | Kutilayotgan: {len(all_matches)-finished}",
        ParagraphStyle("ft",parent=styles["Normal"],fontSize=8,alignment=TA_CENTER,textColor=colors.grey)))
    doc.build(elements)
    return tmp.name
