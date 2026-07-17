import asyncio
import hashlib
import html
import io
import json
import os
import re
import smtplib
import sqlite3
import ssl
import secrets
import time
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

def load_app_version() -> str:
    """Read the application version from the single root VERSION file."""
    candidates = (Path("/app/VERSION"), Path(__file__).resolve().parent.parent / "VERSION")
    for candidate in candidates:
        try:
            value = candidate.read_text(encoding="utf-8").strip()
            if re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", value):
                return value
        except OSError:
            continue
    return "0.0.0"

APP_VERSION = load_app_version()
app = FastAPI(title="MEP Planner API", version=APP_VERSION)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"])

REDMINE_URL = os.getenv("REDMINE_URL", "").rstrip("/")
REDMINE_API_KEY = os.getenv("REDMINE_API_KEY", "")
TAG_FIELD = os.getenv("REDMINE_TAG_FIELD", "Tag").strip()
TAG_VALUE = os.getenv("REDMINE_TAG_VALUE", "MEP").strip()
ENV_FIELD = os.getenv("REDMINE_ENV_FIELD", "Environnement").strip()
START_TIME_FIELD = os.getenv("REDMINE_START_TIME_FIELD", "Heure de début").strip()
END_TIME_FIELD = os.getenv("REDMINE_END_TIME_FIELD", "Heure de fin").strip()
ALLOW_DEMO = os.getenv("ALLOW_DEMO", "false").lower() == "true"
POLL_INTERVAL = max(60, int(os.getenv("POLL_INTERVAL_SECONDS", "300")))
MAX_REDMINE_PAGES = max(1, int(os.getenv("MAX_REDMINE_PAGES", "50")))
TIMEZONE = ZoneInfo(os.getenv("TZ", "Europe/Paris"))
DONE_STATUSES = {v.strip().casefold() for v in os.getenv("DONE_STATUSES", "Done;Closed;Terminé;Terminée;Résolu;Resolved").split(";") if v.strip()}

SMTP_ENABLED = os.getenv("SMTP_ENABLED", "false").lower() == "true"
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "25"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "MEP Planner <mep-planner@localhost>")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "false").lower() == "true"
SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "false").lower() == "true"
SMTP_TIMEOUT = max(5, int(os.getenv("SMTP_TIMEOUT_SECONDS", "15")))
SMTP_RECIPIENTS = [v.strip() for v in os.getenv("SMTP_RECIPIENTS", "").split(";") if v.strip()]
DAILY_EMAIL_ENABLED = os.getenv("DAILY_EMAIL_ENABLED", "true").lower() == "true"
DAILY_EMAIL_HOUR = int(os.getenv("DAILY_EMAIL_HOUR", "8"))
DAILY_EMAIL_MINUTE = int(os.getenv("DAILY_EMAIL_MINUTE", "0"))

BRAND_NAME = os.getenv("BRAND_NAME", "MEP Planner").strip() or "MEP Planner"
BRAND_SUBTITLE = os.getenv("BRAND_SUBTITLE", "Pilotage des mises en production").strip()
BRAND_ACCENT = os.getenv("BRAND_ACCENT", "#5B7CFA").strip() or "#5B7CFA"
BRAND_LOGO_PATH = Path(os.getenv("BRAND_LOGO_PATH", "/app/branding/logo.png"))
COMPANY_NAME_DEFAULT = os.getenv("COMPANY_NAME", "My Company").strip()
COMPANY_SUBTITLE_DEFAULT = os.getenv("COMPANY_SUBTITLE", "IT Operations").strip()
COMPANY_ACCENT_DEFAULT = os.getenv("COMPANY_ACCENT", "").strip()
COMPANY_CONTACT_EMAIL_DEFAULT = os.getenv("COMPANY_CONTACT_EMAIL", "").strip()
COMPANY_FOOTER_DEFAULT = os.getenv("COMPANY_FOOTER", "").strip()
APP_LANGUAGE_DEFAULT = os.getenv("APP_LANGUAGE", "fr").strip().lower() if os.getenv("APP_LANGUAGE", "fr").strip().lower() in {"fr","en"} else "fr"
COMMUNICATION_LANGUAGE_DEFAULT = os.getenv("COMMUNICATION_LANGUAGE", APP_LANGUAGE_DEFAULT).strip().lower() if os.getenv("COMMUNICATION_LANGUAGE", APP_LANGUAGE_DEFAULT).strip().lower() in {"fr","en"} else APP_LANGUAGE_DEFAULT

DATA_DIR = Path("/app/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_FILE = DATA_DIR / "mep_planner.sqlite3"
STATE_FILE = DATA_DIR / "issues_state.json"
COMPANY_LOGO_FILE = DATA_DIR / "branding" / "company-logo.png"
COMPANY_LOGO_FILE.parent.mkdir(parents=True, exist_ok=True)

cache: dict[str, Any] = {"mode":"loading","issues":[],"last_sync":None,"last_attempt":None,"error":None,"pages_read":0,"tickets_read":0}
sync_lock = asyncio.Lock()

class ResendRequest(BaseModel):
    recipients: list[EmailStr] | None = None
    include_pdf: bool = True
    note: str = ""

class BrandingSettings(BaseModel):
    company_name: str = ""
    company_subtitle: str = ""
    company_accent: str = ""
    company_contact_email: str = ""
    company_footer: str = ""
    language: str = "fr"
    communication_language: str = "fr"

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "").strip()
ADMIN_SESSION_HOURS = max(1, int(os.getenv("ADMIN_SESSION_HOURS", "8")))
GITHUB_REPOSITORY_URL = os.getenv("GITHUB_REPOSITORY_URL", "https://github.com/Maxime3d77/MEP-Planner").rstrip("/")
GITHUB_API_REPOSITORY = os.getenv("GITHUB_API_REPOSITORY", "Maxime3d77/MEP-Planner").strip()
GITHUB_CHECK_TIMEOUT_SECONDS = max(3, int(os.getenv("GITHUB_CHECK_TIMEOUT_SECONDS", "8")))
admin_sessions: dict[str, float] = {}

class AdminLoginRequest(BaseModel):
    password: str

def create_admin_session() -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    expires = time.time() + ADMIN_SESSION_HOURS * 3600
    admin_sessions[token] = expires
    return token, datetime.fromtimestamp(expires, TIMEZONE).isoformat(timespec="seconds")

def require_admin(authorization: str | None) -> None:
    if not ADMIN_PASSWORD:
        raise HTTPException(status_code=503, detail="ADMIN_PASSWORD is not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Administrator authentication required")
    token = authorization[7:].strip()
    expires = admin_sessions.get(token, 0)
    if expires <= time.time():
        admin_sessions.pop(token, None)
        raise HTTPException(status_code=401, detail="Administrator session expired")

def version_tuple(value: str) -> tuple[int, ...]:
    match = re.search(r"(\d+(?:\.\d+)+)", value or "")
    return tuple(int(v) for v in match.group(1).split(".")) if match else (0,)

async def github_version_status() -> dict[str, Any]:
    result = {"current_version": APP_VERSION, "latest_version": None, "update_available": False, "repository_url": GITHUB_REPOSITORY_URL, "release_url": None, "status": "unknown", "error": None}
    if not GITHUB_API_REPOSITORY:
        result.update(status="disabled", error="GitHub repository is not configured")
        return result
    headers = {"Accept": "application/vnd.github+json", "User-Agent": f"MEP-Planner/{APP_VERSION}"}
    try:
        async with httpx.AsyncClient(timeout=GITHUB_CHECK_TIMEOUT_SECONDS, follow_redirects=True) as client:
            release = await client.get(f"https://api.github.com/repos/{GITHUB_API_REPOSITORY}/releases/latest", headers=headers)
            if release.status_code == 200:
                data = release.json(); tag = str(data.get("tag_name", ""))
                result.update(latest_version=tag.lstrip("vV"), release_url=data.get("html_url"), status="ok")
            elif release.status_code == 404:
                tags = await client.get(f"https://api.github.com/repos/{GITHUB_API_REPOSITORY}/tags?per_page=1", headers=headers)
                tags.raise_for_status(); items = tags.json()
                if items:
                    tag = str(items[0].get("name", "")); result.update(latest_version=tag.lstrip("vV"), release_url=f"{GITHUB_REPOSITORY_URL}/releases", status="tag")
                else:
                    result.update(status="no_release")
            else:
                release.raise_for_status()
        if result["latest_version"]:
            result["update_available"] = version_tuple(result["latest_version"]) > version_tuple(APP_VERSION)
        return result
    except Exception as exc:
        result.update(status="error", error=str(exc))
        return result


def now_local() -> datetime: return datetime.now(TIMEZONE)

def brand_logo_bytes() -> bytes | None:
    try:return BRAND_LOGO_PATH.read_bytes() if BRAND_LOGO_PATH.is_file() else None
    except OSError:return None

def company_logo_bytes() -> bytes | None:
    try:
        return COMPANY_LOGO_FILE.read_bytes() if COMPANY_LOGO_FILE.is_file() else None
    except OSError:
        return None

def get_setting(key: str, default: str = "") -> str:
    try:
        with db() as con:
            row = con.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return str(row["value"]) if row else default
    except sqlite3.Error:
        return default

def set_setting(key: str, value: str) -> None:
    with db() as con:
        con.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))

def branding_settings() -> dict[str, Any]:
    return {
        "brand_name": BRAND_NAME,
        "brand_subtitle": BRAND_SUBTITLE,
        "brand_accent": safe_accent(),
        "company_name": get_setting("company_name", COMPANY_NAME_DEFAULT),
        "company_subtitle": get_setting("company_subtitle", COMPANY_SUBTITLE_DEFAULT),
        "company_accent": get_setting("company_accent", COMPANY_ACCENT_DEFAULT),
        "company_contact_email": get_setting("company_contact_email", COMPANY_CONTACT_EMAIL_DEFAULT),
        "company_footer": get_setting("company_footer", COMPANY_FOOTER_DEFAULT),
        "company_logo_configured": COMPANY_LOGO_FILE.is_file(),
        "language": get_setting("language", APP_LANGUAGE_DEFAULT),
        "communication_language": get_setting("communication_language", COMMUNICATION_LANGUAGE_DEFAULT),
    }

def safe_accent() -> str:
    value=BRAND_ACCENT.strip()
    return value if re.fullmatch(r"#[0-9A-Fa-f]{6}",value) else "#5B7CFA"

def db() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_FILE, timeout=20)
    connection.row_factory = sqlite3.Row
    return connection

def init_db() -> None:
    with db() as con:
        con.executescript('''
        CREATE TABLE IF NOT EXISTS settings (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS notifications (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          issue_id INTEGER,
          issue_version TEXT NOT NULL,
          notification_type TEXT NOT NULL,
          subject TEXT NOT NULL,
          recipients TEXT NOT NULL,
          recipient_key TEXT NOT NULL,
          sent_at TEXT NOT NULL,
          status TEXT NOT NULL,
          error TEXT,
          message_id TEXT,
          manual INTEGER NOT NULL DEFAULT 0,
          pdf_attached INTEGER NOT NULL DEFAULT 0
        );
        CREATE UNIQUE INDEX IF NOT EXISTS uq_auto_notification
          ON notifications(issue_id, issue_version, notification_type, recipient_key)
          WHERE manual = 0 AND status = 'sent';
        CREATE INDEX IF NOT EXISTS idx_notification_issue ON notifications(issue_id, sent_at DESC);
        ''')

def load_json(path: Path, default: Any) -> Any:
    try: return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError): return default

def save_json(path: Path, value: Any) -> None:
    tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8'); tmp.replace(path)

def custom_field_map(issue: dict[str, Any]) -> dict[str,str]:
    result={}
    for field in issue.get('custom_fields',[]):
        value=field.get('value','')
        if isinstance(value,list): value=', '.join(map(str,value))
        result[str(field.get('name','')).strip()]=str(value).strip()
    return result

def normalize_time(value: str) -> str | None:
    value=(value or '').strip()
    if not value:return None
    try:
        parts=value.replace('h',':').split(':')
        if len(parts) > 2: return None
        hour=int(parts[0]); minute=int(parts[1]) if len(parts)>1 else 0
        if not (0 <= hour <= 23 and 0 <= minute <= 59): return None
        return f"{hour:02d}:{minute:02d}"
    except (ValueError, TypeError):return None

def normalize_issue(raw: dict[str,Any]) -> dict[str,Any]:
    f=custom_field_map(raw); tags=[x.strip() for x in f.get(TAG_FIELD,'').replace(';',',').split(',') if x.strip()]
    start=raw.get('start_date') or str(raw.get('created_on',''))[:10]; due=raw.get('due_date') or start
    estimated=raw.get('estimated_hours') or 0
    try: estimated=float(estimated)
    except (TypeError,ValueError): estimated=0
    start_time=normalize_time(f.get(START_TIME_FIELD,''))
    end_time=normalize_time(f.get(END_TIME_FIELD,''))
    if start_time and not end_time and estimated:
        end_time=(datetime.strptime(start_time,'%H:%M')+timedelta(hours=estimated)).strftime('%H:%M')
    return {'id':raw.get('id'),'subject':raw.get('subject',''),'status':raw.get('status',{}).get('name','—'),'priority':raw.get('priority',{}).get('name','—'),'author':raw.get('author',{}).get('name','—'),'assigned_to':raw.get('assigned_to',{}).get('name','Non assigné'),'start_date':start,'due_date':due,'start_time':start_time,'end_time':end_time,'has_time':bool(start_time),'estimated_hours':estimated,'environment':f.get(ENV_FIELD,'Non défini') or 'Non défini','description':raw.get('description') or 'Aucune description.','tags':tags,'url':f"{REDMINE_URL}/issues/{raw.get('id')}",'updated_on':raw.get('updated_on','')}

def demo_issues() -> list[dict[str,Any]]:
    today=now_local().date().isoformat()
    return [{'id':1258,'subject':'Déploiement correctif - Authentification','status':'To Do','priority':'Immédiat','author':'Julien Martin','assigned_to':'Sophie Dubois','start_date':today,'due_date':today,'start_time':'09:00','end_time':'10:30','has_time':True,'estimated_hours':1.5,'environment':'Production','description':'Correctif d’authentification avec validation et procédure de rollback.','tags':['MEP'],'url':'#','updated_on':now_local().isoformat()}]

def is_mep(i): return any(t.casefold()==TAG_VALUE.casefold() or 'mep urgente' in t.casefold() for t in i.get('tags',[]))
def is_done(i): return str(i.get('status','')).strip().casefold() in DONE_STATUSES

def priority_level(issue: dict[str,Any]) -> int:
    p=str(issue.get('priority','')).strip().casefold()
    if 'immédiat' in p or 'immediat' in p:return 4
    if 'urgent' in p:return 3
    if 'haut' in p or 'high' in p:return 2
    return 1

def issue_signature(issue: dict[str,Any]) -> dict[str,Any]:
    return {k:issue.get(k) for k in ('subject','status','priority','assigned_to','start_date','due_date','start_time','end_time','environment','estimated_hours','updated_on')}

def issue_version(issue: dict[str,Any]) -> str:
    payload=json.dumps(issue_signature(issue),sort_keys=True,ensure_ascii=False).encode(); return hashlib.sha256(payload).hexdigest()[:24]

def recipient_key(recipients:list[str])->str: return hashlib.sha256(';'.join(sorted(x.casefold() for x in recipients)).encode()).hexdigest()[:24]

async def fetch_redmine():
    if not REDMINE_URL or not REDMINE_API_KEY or REDMINE_API_KEY=='change_me':
        if ALLOW_DEMO:return 'demo',demo_issues(),1,1
        raise RuntimeError('Configuration Redmine manquante')
    all_issues=[];seen=set();offset=0;pages=0
    timeout=httpx.Timeout(connect=10,read=25,write=10,pool=10)
    async with httpx.AsyncClient(timeout=timeout,verify=True) as client:
        for idx in range(MAX_REDMINE_PAGES):
            pages=idx+1; print(f'Redmine page {pages}, offset {offset}',flush=True)
            r=await client.get(f'{REDMINE_URL}/issues.json',params={'limit':100,'offset':offset,'status_id':'*','sort':'updated_on:desc'},headers={'X-Redmine-API-Key':REDMINE_API_KEY});r.raise_for_status();p=r.json();batch=p.get('issues',[])
            if not batch:break
            added=0
            for raw in batch:
                if isinstance(raw.get('id'),int) and raw['id'] not in seen:seen.add(raw['id']);all_issues.append(raw);added+=1
            if not added:break
            offset+=len(batch)
            if offset>=int(p.get('total_count',offset)):break
    selected=[i for i in map(normalize_issue,all_issues) if is_mep(i)]
    print(f'Synchronisation terminée : {len(all_issues)} tickets lus, {len(selected)} MEP retenues.',flush=True)
    return 'redmine',selected,pages,len(all_issues)

def communication_language() -> str:
    value=get_setting("communication_language",COMMUNICATION_LANGUAGE_DEFAULT).strip().lower()
    return value if value in {"fr","en"} else "fr"

def tr(fr:str,en:str,lang:str|None=None)->str:
    return en if (lang or communication_language())=="en" else fr

def planning_label(issue: dict[str,Any], lang: str|None=None) -> str:
    if not issue.get("start_time"):
        return f"{issue.get('start_date','—')} · {tr('heure à préciser','time to be confirmed',lang)}"
    ending=f" - {issue.get('end_time')}" if issue.get('end_time') else ""
    return f"{issue.get('start_date','—')} · {issue.get('start_time')}{ending}"

def report_pdf(issue: dict[str,Any], communication: str|None=None, lang: str|None=None) -> bytes:
    lang=lang or communication_language()
    communication=communication or tr('Fiche de communication MEP','Release communication sheet',lang)
    accent = colors.HexColor(safe_accent())
    navy = colors.HexColor('#0B1730'); ink = colors.HexColor('#18243A'); muted = colors.HexColor('#69758C')
    pale = colors.HexColor('#F3F6FC'); line = colors.HexColor('#DCE3F0'); success = colors.HexColor('#187A55')
    priority_color = {4: colors.HexColor('#B20F3B'), 3: colors.HexColor('#D7334B'), 2: colors.HexColor('#C67A11')}.get(priority_level(issue), accent)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=16*mm, leftMargin=16*mm, topMargin=14*mm, bottomMargin=15*mm,
        title=f"MEP #{issue['id']} - {issue['subject']}", author=BRAND_NAME, subject=communication)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BrandEyebrow', parent=styles['BodyText'], fontName='Helvetica-Bold', fontSize=8.5, leading=11, textColor=accent, spaceAfter=2, letterSpacing=1.4))
    styles.add(ParagraphStyle(name='PdfTitle', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=22, leading=26, textColor=navy, alignment=TA_LEFT, spaceAfter=3))
    styles.add(ParagraphStyle(name='PdfSubtitle', parent=styles['BodyText'], fontSize=9.5, leading=13, textColor=muted))
    styles.add(ParagraphStyle(name='IssueTitle', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=17, leading=21, textColor=ink, spaceAfter=2))
    styles.add(ParagraphStyle(name='SectionTitle', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=12, leading=15, textColor=navy, spaceBefore=3, spaceAfter=6))
    styles.add(ParagraphStyle(name='BodyModern', parent=styles['BodyText'], fontSize=9.5, leading=14, textColor=ink))
    styles.add(ParagraphStyle(name='SmallMuted', parent=styles['BodyText'], fontSize=7.8, leading=11, textColor=muted))
    styles.add(ParagraphStyle(name='Footer', parent=styles['BodyText'], fontSize=7.5, leading=10, alignment=TA_CENTER, textColor=muted))
    settings=branding_settings()
    logo_data = brand_logo_bytes()
    company_data = company_logo_bytes()
    logo = Image(io.BytesIO(logo_data), width=16*mm, height=16*mm) if logo_data else ''
    company_logo = Image(io.BytesIO(company_data), width=20*mm, height=16*mm) if company_data else ''
    brand_copy = [Paragraph(html.escape(BRAND_NAME.upper()), styles['BrandEyebrow']), Paragraph(html.escape(communication), styles['PdfTitle']), Paragraph(html.escape(BRAND_SUBTITLE), styles['PdfSubtitle'])]
    company_copy = []
    header = Table([[logo, brand_copy, company_logo, company_copy]], colWidths=[20*mm,132*mm,22*mm,0*mm], hAlign='LEFT')
    header.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0)]))
    pill_style = ParagraphStyle('PriorityPill', parent=styles['BodyText'], alignment=TA_CENTER, fontSize=9, leading=12, textColor=colors.white)
    issue_header = Table([[[Paragraph(f"Ticket #{issue['id']}", styles['BrandEyebrow']), Paragraph(html.escape(issue['subject']), styles['IssueTitle']), Paragraph(f"{html.escape(issue['environment'])} · {html.escape(planning_label(issue,lang))}", styles['PdfSubtitle'])], Paragraph(f"<b>{html.escape(issue['priority'])}</b>", pill_style)]], colWidths=[142*mm,32*mm])
    issue_header.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),pale),('BOX',(0,0),(-1,-1),0.8,line),('LINEBEFORE',(0,0),(0,0),4,priority_color),('BACKGROUND',(1,0),(1,0),priority_color),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(0,0),12),('RIGHTPADDING',(0,0),(0,0),10),('TOPPADDING',(0,0),(-1,-1),11),('BOTTOMPADDING',(0,0),(-1,-1),11)]))
    rows=[(tr('Statut','Status',lang),issue['status'],tr('Environnement','Environment',lang),issue['environment']),(tr('Assigné à','Assigned to',lang),issue['assigned_to'],tr('Auteur','Author',lang),issue['author']),(tr('Début','Start',lang),planning_label(issue,lang),tr('Fin prévue','Expected end',lang),f"{issue['due_date']} {issue.get('end_time') or tr('heure à préciser','time to be confirmed',lang)}"),(tr('Temps estimé','Estimated time',lang),f"{issue['estimated_hours']} h",tr('Dernière mise à jour','Last update',lang),issue.get('updated_on') or '—')]
    data=[]
    for a,b,c,d in rows:
        data.append([Paragraph(f"<b>{html.escape(a)}</b><br/><font color='#69758C'>{html.escape(str(b))}</font>",styles['BodyModern']), Paragraph(f"<b>{html.escape(c)}</b><br/><font color='#69758C'>{html.escape(str(d))}</font>",styles['BodyModern'])])
    info=Table(data,colWidths=[87*mm,87*mm]); info.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.white),('BOX',(0,0),(-1,-1),0.8,line),('INNERGRID',(0,0),(-1,-1),0.5,line),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),9)]))
    description=Table([[Paragraph(html.escape(issue.get('description') or tr('Aucune description.','No description provided.',lang)).replace('\n','<br/>'),styles['BodyModern'])]],colWidths=[174*mm]); description.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),pale),('BOX',(0,0),(-1,-1),0.8,line),('LEFTPADDING',(0,0),(-1,-1),12),('RIGHTPADDING',(0,0),(-1,-1),12),('TOPPADDING',(0,0),(-1,-1),12),('BOTTOMPADDING',(0,0),(-1,-1),12)]))
    communication_text=f"<b>{tr('Communication tracée','Tracked communication',lang)}</b><br/>{tr('Cette fiche a été générée par MEP Planner. La source opérationnelle reste le ticket Redmine.','This sheet was generated by MEP Planner. The Redmine ticket remains the operational source of truth.',lang)}"
    if settings['company_footer']: communication_text += f"<br/><br/>{html.escape(settings['company_footer'])}"
    contact_text=f"<b>{tr('Généré le','Generated on',lang)}</b><br/>{now_local().strftime('%m/%d/%Y at %H:%M' if lang=='en' else '%d/%m/%Y à %H:%M')}"
    if settings['company_contact_email']: contact_text += f"<br/><br/><b>Contact</b><br/>{html.escape(settings['company_contact_email'])}"
    communication_box=Table([[Paragraph(communication_text,styles['SmallMuted']),Paragraph(contact_text,styles['SmallMuted'])]],colWidths=[125*mm,49*mm]); communication_box.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#EAF7F1')),('BOX',(0,0),(-1,-1),0.8,colors.HexColor('#B8E2CF')),('LINEBEFORE',(0,0),(0,0),4,success),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),9)]))
    story=[header,Spacer(1,5*mm),HRFlowable(width='100%',thickness=2,color=accent,spaceAfter=5*mm),issue_header,Spacer(1,5*mm),Paragraph(tr('Informations de planification','Release planning information',lang),styles['SectionTitle']),info,Spacer(1,5*mm),Paragraph(tr('Description et consignes','Description and instructions',lang),styles['SectionTitle']),description,Spacer(1,5*mm),communication_box,Spacer(1,5*mm),Paragraph(f"{tr('Référence','Reference',lang)} : #{issue['id']} · {html.escape(issue['url'])}",styles['Footer'])]
    def decorate(canvas, document):
        canvas.saveState(); width,height=A4; canvas.setFillColor(accent); canvas.rect(0,height-5*mm,width,5*mm,fill=1,stroke=0); canvas.setStrokeColor(line); canvas.line(16*mm,12*mm,width-16*mm,12*mm); canvas.setFont('Helvetica',7); canvas.setFillColor(muted); canvas.drawString(16*mm,7.5*mm,BRAND_NAME); canvas.drawRightString(width-16*mm,7.5*mm,f"{tr('Page','Page',lang)} {document.page}"); canvas.restoreState()
    doc.build(story,onFirstPage=decorate,onLaterPages=decorate); return buf.getvalue()

def email_template(title:str,intro:str,issues:list[dict[str,Any]],note:str='',lang:str|None=None)->str:
    lang=lang or communication_language()
    accent=safe_accent(); cards=[]
    for i in issues:
        level=priority_level(i); card_accent={4:'#B20F3B',3:'#D7334B',2:'#C67A11'}.get(level,accent); label={4:tr('PRIORITÉ MAXIMALE','HIGHEST PRIORITY',lang),3:tr('PRIORITAIRE','PRIORITY',lang),2:tr('TRAITEMENT MOYEN','MEDIUM HANDLING',lang)}.get(level,tr('TRAITEMENT STANDARD','STANDARD HANDLING',lang))
        cards.append(f'''<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:18px 0;background:#111B2E;border:1px solid #2A3958;border-radius:16px;overflow:hidden"><tr><td style="width:6px;background:{card_accent};font-size:0">&nbsp;</td><td style="padding:20px 22px"><div style="display:inline-block;background:{card_accent};color:#fff;border-radius:999px;padding:5px 10px;font-size:10px;font-weight:700;letter-spacing:.8px">{label}</div><div style="margin-top:12px;color:#8FA8CC;font-size:12px;font-weight:700">TICKET #{i['id']} · {html.escape(i['status']).upper()}</div><h2 style="margin:7px 0 16px;color:#FFFFFF;font-size:22px;line-height:1.25">{html.escape(i['subject'])}</h2><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="color:#D6DEEC;font-size:13px;line-height:1.6"><tr><td width="46%" style="padding:6px 0;border-bottom:1px solid #24334E"><span style="color:#7F90AA">{tr('Planification','Schedule',lang)}</span><br><strong>{html.escape(planning_label(i,lang))}</strong></td><td style="padding:6px 0;border-bottom:1px solid #24334E"><span style="color:#7F90AA">{tr('Environnement','Environment',lang)}</span><br><strong>{html.escape(i['environment'])}</strong></td></tr><tr><td style="padding:8px 0"><span style="color:#7F90AA">{tr('Assigné à','Assigned to',lang)}</span><br><strong>{html.escape(i['assigned_to'])}</strong></td><td style="padding:8px 0"><span style="color:#7F90AA">{tr('Priorité Redmine','Redmine priority',lang)}</span><br><strong>{html.escape(i['priority'])}</strong></td></tr></table><div style="margin:14px 0 18px;padding:14px;background:#0B1424;border-radius:10px;color:#B7C2D6;font-size:13px;line-height:1.55;white-space:pre-line">{html.escape(i['description'][:1200])}</div><a href="{html.escape(i['url'])}" style="display:inline-block;background:{accent};color:#fff;text-decoration:none;padding:11px 17px;border-radius:9px;font-weight:700;font-size:13px">{tr('Ouvrir le ticket Redmine','Open Redmine ticket',lang)}</a><span style="display:inline-block;margin-left:10px;color:#7F90AA;font-size:11px">{tr('Fiche PDF jointe selon la configuration','PDF sheet attached according to configuration',lang)}</span></td></tr></table>''')
    note_html=f'''<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:16px 0;background:#FFF5D8;border:1px solid #F1D78B;border-radius:12px"><tr><td style="padding:14px 16px;color:#5F490D;font-size:13px;line-height:1.5"><strong>{tr('Note complémentaire','Additional note',lang)}</strong><br>{html.escape(note)}</td></tr></table>''' if note else ''
    settings=branding_settings()
    logo_html='<img src="cid:mep-planner-logo" width="54" height="54" alt="" style="display:block;border:0;border-radius:12px">' if brand_logo_bytes() else f'<div style="width:54px;height:54px;border-radius:12px;background:{accent};color:#fff;font-size:24px;font-weight:bold;line-height:54px;text-align:center">M</div>'
    return f'''<!doctype html><html lang="{lang}"><body style="margin:0;padding:0;background:#070C15;font-family:Arial,Helvetica,sans-serif"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#070C15"><tr><td align="center" style="padding:28px 12px"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:760px"><tr><td style="background:#13203A;border:1px solid #2B3B5D;border-radius:18px;padding:26px"><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td width="72">{logo_html}</td><td><div style="color:#91B5FF;font-size:11px;letter-spacing:2px;font-weight:700">{html.escape(BRAND_NAME.upper())}</div><div style="color:#8392AA;font-size:11px;margin-top:4px">{html.escape(BRAND_SUBTITLE)}</div></td><td style="padding-left:18px">{('<img src="cid:company-logo" width="72" alt="" style="display:block;max-height:48px;object-fit:contain">' if company_logo_bytes() else '')}</td><td align="right" style="color:#7F90AA;font-size:11px">{tr('Communication MEP','Release communication',lang)}<br>{now_local().strftime('%d/%m/%Y · %H:%M')}</td></tr></table><h1 style="margin:24px 0 8px;color:#FFFFFF;font-size:30px;line-height:1.15">{html.escape(title)}</h1><p style="margin:0;color:#B9C5D8;font-size:15px;line-height:1.55">{html.escape(intro)}</p></td></tr><tr><td>{note_html}{''.join(cards)}</td></tr><tr><td style="padding:8px 12px 0;text-align:center;color:#65728A;font-size:10px;line-height:1.5">Communication envoyée et historisée par {html.escape(BRAND_NAME)}.<br>{html.escape(settings['company_footer']) if settings['company_footer'] else tr('Ne répondez pas à ce message automatique sauf indication contraire.','Do not reply to this automated message unless instructed otherwise.',lang)}{('<br>Contact : ' + html.escape(settings['company_contact_email'])) if settings['company_contact_email'] else ''}</td></tr></table></td></tr></table></body></html>'''

def smtp_send(subject:str,html_body:str,recipients:list[str],attachment:bytes|None=None,filename:str|None=None,lang:str|None=None)->str:
    if not SMTP_ENABLED:raise RuntimeError('SMTP désactivé dans .env')
    if not SMTP_HOST:raise RuntimeError('SMTP_HOST non configuré')
    if not recipients:raise RuntimeError('Aucun destinataire')
    msg=EmailMessage(); msg['Subject']=subject; msg['From']=SMTP_FROM; msg['To']=', '.join(recipients); msg['Message-ID']=f"<{hashlib.sha256((subject+str(now_local().timestamp())).encode()).hexdigest()[:24]}@mep-planner>"
    lang=lang or communication_language()
    msg.set_content(f"{subject}\n\n{tr('Cette communication a été envoyée par MEP Planner. Consultez la version HTML ou la fiche PDF jointe.','This communication was sent by MEP Planner. See the HTML version or the attached PDF sheet.',lang)}")
    msg.add_alternative(html_body,subtype='html')
    logo=brand_logo_bytes()
    if logo:
        subtype='png'; suffix=BRAND_LOGO_PATH.suffix.lower()
        if suffix in {'.jpg','.jpeg'}:subtype='jpeg'
        elif suffix=='.gif':subtype='gif'
        msg.get_payload()[-1].add_related(logo,maintype='image',subtype=subtype,cid='<mep-planner-logo>',filename=BRAND_LOGO_PATH.name,disposition='inline')
    company_logo=company_logo_bytes()
    if company_logo:
        msg.get_payload()[-1].add_related(company_logo,maintype='image',subtype='png',cid='<company-logo>',filename='company-logo.png',disposition='inline')
    if attachment:msg.add_attachment(attachment,maintype='application',subtype='pdf',filename=filename or 'rapport-mep.pdf')
    if SMTP_USE_SSL:
        with smtplib.SMTP_SSL(SMTP_HOST,SMTP_PORT,timeout=SMTP_TIMEOUT,context=ssl.create_default_context()) as smtp:
            if SMTP_USERNAME:smtp.login(SMTP_USERNAME,SMTP_PASSWORD)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(SMTP_HOST,SMTP_PORT,timeout=SMTP_TIMEOUT) as smtp:
            smtp.ehlo()
            if SMTP_USE_TLS:smtp.starttls(context=ssl.create_default_context());smtp.ehlo()
            if SMTP_USERNAME:smtp.login(SMTP_USERNAME,SMTP_PASSWORD)
            smtp.send_message(msg)
    return str(msg['Message-ID'])

def already_sent(issue_id:int|None,version:str,kind:str,recipients:list[str])->bool:
    with db() as con:return con.execute("SELECT 1 FROM notifications WHERE issue_id IS ? AND issue_version=? AND notification_type=? AND recipient_key=? AND manual=0 AND status='sent' LIMIT 1",(issue_id,version,kind,recipient_key(recipients))).fetchone() is not None

def record(issue_id,version,kind,subject,recipients,status,error='',message_id='',manual=False,pdf=False):
    with db() as con: con.execute('INSERT INTO notifications(issue_id,issue_version,notification_type,subject,recipients,recipient_key,sent_at,status,error,message_id,manual,pdf_attached) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(issue_id,version,kind,subject,';'.join(recipients),recipient_key(recipients),now_local().isoformat(timespec='seconds'),status,error,message_id,int(manual),int(pdf)))

def deliver(issue:dict[str,Any],kind:str,subject:str,intro:str,recipients:list[str],manual=False,include_pdf=True,note='')->dict[str,Any]:
    version=issue_version(issue)
    if not manual and already_sent(issue['id'],version,kind,recipients):return {'sent':False,'duplicate':True}
    try:
        lang=communication_language();pdf=report_pdf(issue,lang=lang) if include_pdf else None;filename=f"{'release-sheet' if lang=='en' else 'fiche-mep'}-{issue['id']}.pdf" if pdf else None;message_id=smtp_send(subject,email_template(subject,intro,[issue],note,lang),recipients,pdf,filename,lang);record(issue['id'],version,kind,subject,recipients,'sent',message_id=message_id,manual=manual,pdf=bool(pdf));return {'sent':True,'duplicate':False}
    except Exception as exc:
        record(issue['id'],version,kind,subject,recipients,'error',error=str(exc),manual=manual,pdf=include_pdf);raise

def issue_by_id(issue_id:int)->dict[str,Any]:
    issue=next((i for i in cache.get('issues',[]) if i.get('id')==issue_id),None)
    if not issue:raise HTTPException(404,'MEP introuvable')
    return issue

def notification_summary(issue_id:int)->dict[str,Any]:
    with db() as con: rows=con.execute('SELECT * FROM notifications WHERE issue_id=? ORDER BY sent_at DESC',(issue_id,)).fetchall()
    if not rows:return {'sent':False,'last':None,'count':0,'recipients':[],'errors':0}
    successful=[r for r in rows if r['status']=='sent'];last=successful[0] if successful else rows[0]
    return {'sent':bool(successful),'last':dict(last),'count':len(successful),'recipients':last['recipients'].split(';') if last['recipients'] else [],'errors':sum(r['status']=='error' for r in rows)}

async def send_change_notifications(previous,current,issues):
    if not previous or not SMTP_ENABLED or not SMTP_RECIPIENTS:return
    by_id={str(i['id']):i for i in issues}
    for key in [k for k in current if k not in previous]:
        try: await asyncio.to_thread(deliver,by_id[key],'new',f"{tr('Nouvelle MEP planifiée','New scheduled release')} - #{key}",tr('Une nouvelle mise en production a été détectée.','A new production release has been detected.'),SMTP_RECIPIENTS,False,True,'')
        except Exception as e:print(f'Erreur SMTP nouvelle MEP #{key}: {e}',flush=True)
    for key in [k for k in current if k in previous and current[k]!=previous[k]]:
        try: await asyncio.to_thread(deliver,by_id[key],'changed',f"{tr('MEP modifiée','Release updated')} - #{key}",tr('Les informations de cette MEP ont été modifiées.','The information for this release has been updated.'),SMTP_RECIPIENTS,False,True,'')
        except Exception as e:print(f'Erreur SMTP modification MEP #{key}: {e}',flush=True)

async def synchronize(initial=False):
    global cache
    if sync_lock.locked():return
    async with sync_lock:
        cache['last_attempt']=now_local().isoformat(timespec='seconds')
        try:
            mode,issues,pages,tickets=await fetch_redmine();previous=load_json(STATE_FILE,{});current={str(i['id']):issue_signature(i) for i in issues};cache={'mode':mode,'issues':issues,'last_sync':now_local().isoformat(timespec='seconds'),'last_attempt':cache['last_attempt'],'error':None,'pages_read':pages,'tickets_read':tickets};save_json(STATE_FILE,current)
            if not initial:await send_change_notifications(previous,current,issues)
        except Exception as e:cache['error']=f'{type(e).__name__}: {e}';print(f"Erreur synchronisation Redmine : {cache['error']}",flush=True)

async def watcher():
    await synchronize(initial=True)
    while True:await asyncio.sleep(POLL_INTERVAL);await synchronize(False)

async def daily_mailer():
    while True:
        now=now_local();target=now.replace(hour=DAILY_EMAIL_HOUR,minute=DAILY_EMAIL_MINUTE,second=0,microsecond=0)
        if target<=now:target+=timedelta(days=1)
        await asyncio.sleep(max(1,(target-now).total_seconds()))
        if not DAILY_EMAIL_ENABLED or not SMTP_ENABLED or not SMTP_RECIPIENTS:continue
        today=now_local().date().isoformat()
        for issue in [i for i in cache.get('issues',[]) if i.get('start_date')==today and not is_done(i)]:
            try:await asyncio.to_thread(deliver,issue,'daily',f"{tr('MEP du jour',"Today's release")} - #{issue['id']}",tr('Rappel de la mise en production prévue aujourd’hui.',"Reminder for today's scheduled production release."),SMTP_RECIPIENTS,False,True,'')
            except Exception as e:print(f"Erreur e-mail quotidien #{issue['id']}: {e}",flush=True)

@app.on_event('startup')
async def startup():init_db();asyncio.create_task(watcher());asyncio.create_task(daily_mailer())

@app.get('/api/health')
async def health():return {'status':'ok','version':APP_VERSION,'mode':cache['mode'],'syncing':sync_lock.locked(),'last_sync':cache['last_sync'],'last_attempt':cache['last_attempt'],'pages_read':cache['pages_read'],'tickets_read':cache['tickets_read'],'mep_count':len(cache.get('issues',[])),'error':cache['error']}

@app.get('/api/issues')
async def issues():
    data=[]
    for issue in cache.get('issues',[]):data.append({**issue,'priority_level':priority_level(issue),'notification':notification_summary(issue['id'])})
    return {'mode':cache['mode'],'syncing':sync_lock.locked(),'last_sync':cache['last_sync'],'issues':[i for i in data if not is_done(i)],'history':[i for i in data if is_done(i)],'error':cache['error']}

@app.post('/api/refresh')
async def refresh():
    if not sync_lock.locked():asyncio.create_task(synchronize(False))
    return {'status':'accepted','syncing':True}

@app.get('/api/notifications')
async def notifications(issue_id:int|None=None,limit:int=Query(200,ge=1,le=1000)):
    with db() as con:
        if issue_id is None:rows=con.execute('SELECT * FROM notifications ORDER BY sent_at DESC LIMIT ?',(limit,)).fetchall()
        else:rows=con.execute('SELECT * FROM notifications WHERE issue_id=? ORDER BY sent_at DESC LIMIT ?',(issue_id,limit)).fetchall()
    return {'notifications':[dict(r) for r in rows]}

@app.post('/api/issues/{issue_id}/resend')
async def resend(issue_id:int,payload:ResendRequest):
    issue=issue_by_id(issue_id);recipients=[str(x) for x in payload.recipients] if payload.recipients else SMTP_RECIPIENTS
    if not recipients:raise HTTPException(400,'Aucun destinataire configuré')
    try:return await asyncio.to_thread(deliver,issue,'manual',f"{tr('Renvoi communication MEP','Release communication resend')} - #{issue_id}",tr('Renvoi manuel demandé depuis MEP Planner.','Manual resend requested from MEP Planner.'),recipients,True,payload.include_pdf,payload.note)
    except Exception as e:raise HTTPException(502,str(e)) from e

@app.post('/api/admin/login')
async def admin_login(payload: AdminLoginRequest):
    if not ADMIN_PASSWORD:
        raise HTTPException(status_code=503, detail="ADMIN_PASSWORD is not configured")
    if not secrets.compare_digest(payload.password, ADMIN_PASSWORD):
        raise HTTPException(status_code=401, detail="Invalid administrator password")
    token, expires_at = create_admin_session()
    return {"token": token, "expires_at": expires_at}

@app.get('/api/admin/session')
async def admin_session(authorization: str | None = Header(default=None)):
    require_admin(authorization)
    return {"authenticated": True}

@app.get('/api/version/check')
async def version_check():
    return await github_version_status()

@app.get('/api/settings')
async def get_settings():
    return branding_settings()

@app.put('/api/settings')
async def update_settings(payload: BrandingSettings, authorization: str | None = Header(default=None)):
    require_admin(authorization)
    accent=payload.company_accent.strip()
    if accent and not re.fullmatch(r"#[0-9A-Fa-f]{6}",accent):
        raise HTTPException(400,"La couleur doit être au format #RRGGBB")
    values=payload.model_dump()
    for key,value in values.items():
        set_setting(key,str(value).strip())
    return branding_settings()

@app.post('/api/settings/company-logo')
async def upload_company_logo(file: UploadFile = File(...), authorization: str | None = Header(default=None)):
    require_admin(authorization)
    if file.content_type != "image/png":
        raise HTTPException(400,"Format accepté : PNG uniquement")
    content=await file.read()
    if len(content)>3*1024*1024:
        raise HTTPException(400,"Logo trop volumineux (maximum 3 Mo)")
    COMPANY_LOGO_FILE.write_bytes(content)
    return {"status":"ok","company_logo_configured":True}

@app.delete('/api/settings/company-logo')
async def delete_company_logo(authorization: str | None = Header(default=None)):
    require_admin(authorization)
    COMPANY_LOGO_FILE.unlink(missing_ok=True)
    return {"status":"ok","company_logo_configured":False}

@app.get('/api/settings/company-logo')
async def serve_company_logo():
    if not COMPANY_LOGO_FILE.is_file():
        raise HTTPException(404,"Aucun logo entreprise")
    return Response(COMPANY_LOGO_FILE.read_bytes(),media_type='image/png',headers={'Cache-Control':'no-store'})

@app.get('/api/issues/{issue_id}/report.pdf')
async def pdf_report(issue_id:int):
    issue=issue_by_id(issue_id);content=await asyncio.to_thread(report_pdf,issue,None,communication_language())
    return Response(content,media_type='application/pdf',headers={'Content-Disposition':f'inline; filename="MEP-{issue_id}.pdf"'})
