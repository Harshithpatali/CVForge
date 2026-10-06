"""CVForge — evidence-first resume tailoring (Streamlit front-end).

Run locally with:  streamlit run app.py
"""

from __future__ import annotations

import copy
import html
import re
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import streamlit as st

from api_client import API_URL, APIError, auth, download, get, post, put, request

# --------------------------------------------------------------------------- #
# Page configuration  (must be the first Streamlit call)
# --------------------------------------------------------------------------- #

st.set_page_config(
    page_title="CVForge Studio — AI Resume Workspace",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------------------------------- #
# Streamlit version compatibility
# --------------------------------------------------------------------------- #

def _full_width_kwargs() -> Dict[str, Any]:
    """`use_container_width` was replaced by `width="stretch"` in Streamlit 1.49."""
    try:
        major, minor = (int(part) for part in st.__version__.split(".")[:2])
    except Exception:
        return {"use_container_width": True}
    return {"width": "stretch"} if (major, minor) >= (1, 49) else {"use_container_width": True}


FW: Dict[str, Any] = _full_width_kwargs()

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
URL_RE = re.compile(r"https?://[^\s|<>]+")

UI_BUILD = "studio-ui-2026.10.06"

NAV_ITEMS: Tuple[Tuple[str, str], ...] = (
    ("Dashboard", "⌂"),
    ("CV Studio", "✦"),
    ("Applications", "▦"),
    ("Profiles", "◌"),
)


# --------------------------------------------------------------------------- #
# Design system
# --------------------------------------------------------------------------- #

APP_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root{
  --cvf-bg:#f6f7fb;
  --cvf-surface:#ffffff;
  --cvf-surface-2:#f8fafc;
  --cvf-border:#e4e7ec;
  --cvf-border-strong:#d0d5dd;
  --cvf-text:#0f172a;
  --cvf-muted:#667085;
  --cvf-accent:#4f46e5;
  --cvf-accent-dark:#4338ca;
  --cvf-accent-weak:#eef2ff;
  --cvf-success:#059669;
  --cvf-warning:#d97706;
  --cvf-danger:#dc2626;
  --cvf-radius:14px;
  --cvf-shadow-sm:0 1px 2px rgba(16,24,40,.06);
  --cvf-shadow:0 1px 3px rgba(16,24,40,.08), 0 12px 28px -18px rgba(16,24,40,.30);
}

/* ---------- Global ---------- */
.stApp{background:var(--cvf-bg);}
html, body, .stApp, [data-testid="stSidebar"]{
  font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
}
.block-container{max-width:1240px;padding:2.2rem 2rem 5rem;}
#MainMenu, footer{visibility:hidden;}
[data-testid="stHeader"]{background:transparent;}
[data-testid="stToolbar"]{right:.5rem;}

h1,h2,h3,h4,h5{color:var(--cvf-text);letter-spacing:-.02em;}
p, li{color:var(--cvf-text);}
label, .stTextInput label, .stTextArea label, .stSelectbox label, .stFileUploader label{
  font-weight:600 !important; font-size:.86rem !important; color:var(--cvf-text) !important;
}
[data-testid="stWidgetLabel"] p{font-weight:600;font-size:.86rem;color:var(--cvf-text);}
[data-testid="stCaptionContainer"], .stCaption, small{color:var(--cvf-muted) !important;}
a{color:var(--cvf-accent-dark);}

/* ---------- Cards ---------- */
div[data-testid="stVerticalBlockBorderWrapper"]{
  background:var(--cvf-surface);
  border:1px solid var(--cvf-border) !important;
  border-radius:var(--cvf-radius) !important;
  box-shadow:var(--cvf-shadow-sm);
}

/* ---------- Buttons ---------- */
.stButton > button,
.stDownloadButton > button,
.stFormSubmitButton > button,
[data-testid="stFormSubmitButton"] > button{
  border-radius:10px;
  font-weight:600;
  font-size:.9rem;
  padding:.5rem .95rem;
  border:1px solid var(--cvf-border-strong);
  background:var(--cvf-surface);
  color:var(--cvf-text);
  box-shadow:var(--cvf-shadow-sm);
  transition:background .15s ease, border-color .15s ease, color .15s ease, box-shadow .15s ease;
}
.stButton > button:hover,
.stDownloadButton > button:hover,
.stFormSubmitButton > button:hover{
  border-color:var(--cvf-accent);
  color:var(--cvf-accent-dark);
  background:var(--cvf-accent-weak);
}
.stButton > button:focus-visible,
.stDownloadButton > button:focus-visible{
  outline:none;
  box-shadow:0 0 0 3px rgba(79,70,229,.28);
}
.stButton > button[kind="primary"],
.stButton > button[data-testid="stBaseButton-primary"],
.stButton > button[data-testid="baseButton-primary"],
.stFormSubmitButton > button[kind="primary"],
[data-testid="stFormSubmitButton"] > button[kind="primary"]{
  background:var(--cvf-accent);
  border-color:var(--cvf-accent);
  color:#ffffff;
  box-shadow:0 1px 2px rgba(79,70,229,.35), 0 10px 22px -12px rgba(79,70,229,.7);
}
.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="stBaseButton-primary"]:hover,
.stFormSubmitButton > button[kind="primary"]:hover,
[data-testid="stFormSubmitButton"] > button[kind="primary"]:hover{
  background:var(--cvf-accent-dark);
  border-color:var(--cvf-accent-dark);
  color:#ffffff;
}
.stButton > button:disabled,
.stFormSubmitButton > button:disabled{
  opacity:.45;
  box-shadow:none;
}

/* ---------- Inputs ---------- */
div[data-baseweb="input"],
div[data-baseweb="textarea"],
div[data-baseweb="select"] > div{
  border-radius:10px !important;
  border-color:var(--cvf-border-strong) !important;
  background:var(--cvf-surface) !important;
}
div[data-baseweb="input"]:focus-within,
div[data-baseweb="textarea"]:focus-within{
  border-color:var(--cvf-accent) !important;
  box-shadow:0 0 0 3px rgba(79,70,229,.15) !important;
}
input, textarea{font-size:.92rem !important;color:var(--cvf-text) !important;}
[data-testid="stFileUploaderDropzone"]{
  border-radius:12px;
  border:1px dashed var(--cvf-border-strong);
  background:var(--cvf-surface-2);
}

/* ---------- Tabs ---------- */
.stTabs [data-baseweb="tab-list"]{
  gap:.3rem;
  border-bottom:1px solid var(--cvf-border);
  background:transparent;
}
.stTabs [data-baseweb="tab"]{
  height:auto;
  padding:.45rem .85rem;
  border-radius:9px 9px 0 0;
  font-weight:600;
  font-size:.875rem;
  color:var(--cvf-muted);
}
.stTabs [aria-selected="true"]{
  color:var(--cvf-accent-dark) !important;
  background:var(--cvf-accent-weak);
}
.stTabs [data-baseweb="tab-highlight"]{background:var(--cvf-accent);}
.stTabs [data-baseweb="tab-border"]{background:transparent;}

/* ---------- Expanders ---------- */
[data-testid="stExpander"] details{
  border:1px solid var(--cvf-border);
  border-radius:12px;
  background:var(--cvf-surface);
  box-shadow:none;
  overflow:hidden;
}
[data-testid="stExpander"] summary{font-weight:600;font-size:.9rem;}
[data-testid="stExpander"] summary:hover{color:var(--cvf-accent-dark);}

/* ---------- Alerts ---------- */
[data-testid="stAlert"]{border-radius:12px;border:1px solid var(--cvf-border);}

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"]{
  background:var(--cvf-surface);
  border-right:1px solid var(--cvf-border);
}
[data-testid="stSidebar"] .block-container,
[data-testid="stSidebar"] [data-testid="stVerticalBlock"]{padding-top:.4rem;}
[data-testid="stSidebar"] hr{margin:.9rem 0;}
[data-testid="stSidebar"] .stButton > button{
  justify-content:flex-start;
  text-align:left;
  width:100%;
  background:transparent;
  border:1px solid transparent;
  box-shadow:none;
  color:var(--cvf-muted);
  font-weight:600;
  padding:.5rem .7rem;
}
[data-testid="stSidebar"] .stButton > button:hover{
  background:var(--cvf-surface-2);
  color:var(--cvf-text);
  border-color:transparent;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"],
[data-testid="stSidebar"] .stButton > button[data-testid="stBaseButton-primary"],
[data-testid="stSidebar"] .stButton > button[data-testid="baseButton-primary"]{
  background:var(--cvf-accent-weak);
  color:var(--cvf-accent-dark);
  border-color:transparent;
  box-shadow:none;
}

/* ---------- Custom components ---------- */
.cvf-hero{padding:.4rem 0 .6rem;}
.cvf-eyebrow{
  font-size:.72rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;
  color:var(--cvf-accent);
}
.cvf-title{
  font-size:2.05rem;font-weight:800;letter-spacing:-.03em;
  color:var(--cvf-text);margin:.3rem 0 .45rem;line-height:1.15;
}
.cvf-sub{color:var(--cvf-muted);font-size:.97rem;line-height:1.6;max-width:70ch;}

.cvf-brand{display:flex;align-items:center;gap:.7rem;padding:.2rem 0 .9rem;}
.cvf-brand__mark{
  width:2.4rem;height:2.4rem;border-radius:12px;flex:0 0 auto;
  background:linear-gradient(135deg,#4f46e5,#7c3aed);
  color:#fff;display:flex;align-items:center;justify-content:center;
  font-weight:800;font-size:.9rem;letter-spacing:-.02em;
}
.cvf-brand__name{font-weight:800;font-size:1.02rem;letter-spacing:-.02em;color:var(--cvf-text);}
.cvf-brand__tag{font-size:.72rem;color:var(--cvf-muted);}

.cvf-user{display:flex;align-items:center;gap:.6rem;padding:.55rem .6rem;border-radius:12px;background:var(--cvf-surface-2);border:1px solid var(--cvf-border);margin-bottom:.9rem;}
.cvf-user__avatar{
  width:2rem;height:2rem;border-radius:50%;flex:0 0 auto;
  background:var(--cvf-accent-weak);color:var(--cvf-accent-dark);
  display:flex;align-items:center;justify-content:center;font-weight:700;font-size:.82rem;
}
.cvf-user__body{min-width:0;}
.cvf-user__name{font-weight:650;font-size:.86rem;color:var(--cvf-text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.cvf-user__mail{font-size:.74rem;color:var(--cvf-muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}

.cvf-chip{
  display:inline-block;padding:.26rem .58rem;margin:.14rem .28rem .14rem 0;
  border-radius:999px;background:var(--cvf-accent-weak);color:var(--cvf-accent-dark);
  font-size:.76rem;font-weight:600;line-height:1.4;
}
.cvf-chip--muted{background:var(--cvf-surface-2);color:var(--cvf-muted);border:1px solid var(--cvf-border);}
.cvf-chip--success{background:rgba(5,150,105,.10);color:var(--cvf-success);}
.cvf-chip--warning{background:rgba(217,119,6,.12);color:var(--cvf-warning);}
.cvf-chip--danger{background:rgba(220,38,38,.10);color:var(--cvf-danger);}
.cvf-chip--info{background:rgba(79,70,229,.10);color:var(--cvf-accent-dark);}

.cvf-stat{
  display:flex;flex-direction:column;gap:.2rem;height:100%;
  padding:1rem 1.1rem;border-radius:var(--cvf-radius);
  background:var(--cvf-surface);border:1px solid var(--cvf-border);
  box-shadow:var(--cvf-shadow-sm);
}
.cvf-stat__label{font-size:.72rem;font-weight:700;color:var(--cvf-muted);text-transform:uppercase;letter-spacing:.08em;}
.cvf-stat__value{font-size:1.85rem;font-weight:800;color:var(--cvf-text);line-height:1.15;letter-spacing:-.03em;}
.cvf-stat__hint{font-size:.79rem;color:var(--cvf-muted);}

.cvf-steps{display:flex;flex-wrap:wrap;gap:.45rem;margin:.4rem 0 1.1rem;}
.cvf-step{
  display:flex;align-items:center;gap:.45rem;
  padding:.34rem .8rem .34rem .38rem;border-radius:999px;
  font-size:.81rem;font-weight:600;
  border:1px solid var(--cvf-border);background:var(--cvf-surface);color:var(--cvf-muted);
}
.cvf-step__dot{
  display:inline-flex;align-items:center;justify-content:center;
  width:1.35rem;height:1.35rem;border-radius:50%;
  background:var(--cvf-surface-2);font-size:.72rem;font-weight:700;color:var(--cvf-muted);
}
.cvf-step--active{border-color:var(--cvf-accent);background:var(--cvf-accent-weak);color:var(--cvf-accent-dark);}
.cvf-step--active .cvf-step__dot{background:var(--cvf-accent);color:#fff;}
.cvf-step--done{border-color:rgba(5,150,105,.35);background:rgba(5,150,105,.08);color:var(--cvf-success);}
.cvf-step--done .cvf-step__dot{background:var(--cvf-success);color:#fff;}

.cvf-ring-row{display:flex;flex-wrap:wrap;gap:1.4rem;justify-content:space-between;}
.cvf-ring{display:flex;flex-direction:column;align-items:center;gap:.45rem;flex:1 1 0;min-width:118px;}
.cvf-ring__chart{position:relative;width:110px;height:110px;}
.cvf-ring__value{
  position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
  font-size:1.2rem;font-weight:800;color:var(--cvf-text);letter-spacing:-.02em;
}
.cvf-ring__label{font-size:.79rem;font-weight:600;color:var(--cvf-muted);text-align:center;}

.cvf-empty{
  padding:1.8rem 1.5rem;border:1px dashed var(--cvf-border-strong);border-radius:var(--cvf-radius);
  background:var(--cvf-surface);text-align:center;color:var(--cvf-muted);
}
.cvf-empty__title{font-weight:700;color:var(--cvf-text);font-size:1rem;margin-bottom:.25rem;}

.cvf-divider{height:1px;background:var(--cvf-border);margin:1.6rem 0;border:0;}
.cvf-muted{color:var(--cvf-muted);font-size:.85rem;}

.cvf-feature{display:flex;gap:.8rem;align-items:flex-start;padding:.75rem 0;border-bottom:1px solid var(--cvf-border);}
.cvf-feature:last-child{border-bottom:0;}
.cvf-feature__icon{
  width:2.1rem;height:2.1rem;border-radius:10px;flex:0 0 auto;
  background:var(--cvf-accent-weak);display:flex;align-items:center;justify-content:center;font-size:1rem;
}
.cvf-feature__title{font-weight:700;font-size:.93rem;color:var(--cvf-text);}
.cvf-feature__body{font-size:.85rem;color:var(--cvf-muted);line-height:1.55;}

.cvf-resume-name{font-size:1.45rem;font-weight:800;letter-spacing:-.02em;color:var(--cvf-text);}
.cvf-headline{font-size:.95rem;font-weight:600;color:var(--cvf-accent-dark);margin:.15rem 0 .4rem;}
.cvf-section-title{
  font-size:.74rem;font-weight:800;letter-spacing:.11em;text-transform:uppercase;
  color:var(--cvf-muted);margin:1.1rem 0 .4rem;
}
.cvf-repo{border-left:3px solid var(--cvf-accent);padding-left:.85rem;margin:.35rem 0;}
.cvf-repo__name{font-weight:700;color:var(--cvf-text);}

.cvf-workspace-hero{
  display:grid;
  grid-template-columns:minmax(0,1.7fr) minmax(260px,.9fr);
  gap:1rem;
  margin-bottom:1.1rem;
}
.cvf-hero-card{
  background:linear-gradient(135deg,#ffffff 0%,#f8faff 100%);
  border:1px solid var(--cvf-border);
  border-radius:18px;
  padding:1.35rem 1.45rem;
  box-shadow:var(--cvf-shadow);
}
.cvf-hero-card--soft{
  background:linear-gradient(135deg,#f7f5ff 0%,#f3fbf8 100%);
}
.cvf-hero-card__eyebrow{
  font-size:.7rem;font-weight:800;letter-spacing:.13em;text-transform:uppercase;
  color:var(--cvf-accent);margin-bottom:.45rem;
}
.cvf-hero-card__title{
  font-size:1.55rem;font-weight:800;letter-spacing:-.03em;line-height:1.15;
  color:var(--cvf-text);margin-bottom:.45rem;
}
.cvf-hero-card__body{
  color:var(--cvf-muted);font-size:.9rem;line-height:1.6;max-width:62ch;
}
.cvf-model-row{display:flex;flex-wrap:wrap;gap:.45rem;margin-top:.8rem;}
.cvf-model{
  display:inline-flex;align-items:center;gap:.35rem;padding:.32rem .6rem;border-radius:999px;
  font-size:.72rem;font-weight:700;border:1px solid var(--cvf-border);background:#fff;
}
.cvf-model--groq{color:#4338ca;border-color:rgba(79,70,229,.2);background:#eef2ff;}
.cvf-model--gemini{color:#047857;border-color:rgba(5,150,105,.2);background:#ecfdf5;}
.cvf-mini-title{font-size:.82rem;font-weight:800;color:var(--cvf-text);margin-bottom:.55rem;}
.cvf-mini-step{display:flex;gap:.6rem;align-items:flex-start;margin:.55rem 0;}
.cvf-mini-step__n{
  width:1.55rem;height:1.55rem;border-radius:50%;background:var(--cvf-accent-weak);
  color:var(--cvf-accent-dark);display:flex;align-items:center;justify-content:center;
  font-size:.72rem;font-weight:800;flex:0 0 auto;
}
.cvf-mini-step__body{font-size:.78rem;line-height:1.45;color:var(--cvf-muted);}
.cvf-mini-step__body strong{color:var(--cvf-text);}
.cvf-form-shell{
  background:var(--cvf-surface);
  border:1px solid var(--cvf-border);
  border-radius:18px;
  box-shadow:var(--cvf-shadow);
  padding:1.15rem 1.2rem 1.2rem;
  margin-bottom:1rem;
}
.cvf-form-head{
  display:flex;align-items:center;justify-content:space-between;gap:1rem;margin-bottom:.85rem;
}
.cvf-form-title{font-size:1rem;font-weight:800;color:var(--cvf-text);}
.cvf-form-sub{font-size:.78rem;color:var(--cvf-muted);}
.cvf-step-number{
  width:2rem;height:2rem;border-radius:10px;background:var(--cvf-accent);
  color:#fff;font-weight:800;display:inline-flex;align-items:center;justify-content:center;
}
.cvf-upload-card{
  border:1px dashed var(--cvf-border-strong);
  border-radius:14px;padding:.7rem .85rem;background:var(--cvf-surface-2);
}
.cvf-action-row{
  display:flex;align-items:center;justify-content:space-between;gap:.8rem;
  padding:.85rem .95rem;border-radius:14px;background:#0f172a;color:#fff;margin-top:.9rem;
}
.cvf-action-row__copy strong{display:block;font-size:.84rem;color:#fff;}
.cvf-action-row__copy span{font-size:.74rem;color:#cbd5e1;}
@media (max-width:900px){
  .cvf-workspace-hero{grid-template-columns:1fr;}
}
</style>
"""

st.markdown(APP_CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Session state
# --------------------------------------------------------------------------- #

_SESSION_DEFAULTS: Dict[str, Any] = {
    "token": None,
    "user": None,
    "analysis": None,
    "application": None,
    "resume": None,
    "github_repos": [],
    "link_answers": {},
    "page": "Overview",
    "form_seq": 0,
    "flash": None,
    "api_cache": {},
    "draft_candidate": None,
    "draft_candidate_seq": None,
}

for _key, _value in _SESSION_DEFAULTS.items():
    st.session_state.setdefault(_key, _value)


def reset_session() -> None:
    for key in ("token", "user", "analysis", "application", "resume"):
        st.session_state[key] = None
    st.session_state.github_repos = []
    st.session_state.link_answers = {}
    st.session_state.api_cache = {}
    st.session_state.draft_candidate = None
    st.session_state.draft_candidate_seq = None
    st.session_state.page = "Dashboard"


def flash(kind: str, message: str) -> None:
    st.session_state.flash = {"kind": kind, "message": message}


def render_flash() -> None:
    payload = st.session_state.pop("flash", None)
    if not payload:
        return
    kind = payload.get("kind", "info")
    message = payload.get("message", "")
    if not message:
        return
    if kind == "success":
        st.toast(message, icon="✅")
    elif kind == "warning":
        st.warning(message, icon="⚠️")
    elif kind == "error":
        st.error(message, icon="🚫")
    else:
        st.toast(message, icon="ℹ️")


def show_error(exc: Exception) -> None:
    """Surface an API error, transparently handling expired sessions."""
    if isinstance(exc, APIError) and exc.is_auth_error:
        reset_session()
        flash("warning", "Your session expired. Please sign in again.")
        st.rerun()
    st.error(str(exc), icon="🚫")


# --------------------------------------------------------------------------- #
# Small presentation helpers
# --------------------------------------------------------------------------- #

def esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


def normalise_url(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    if not value.startswith(("http://", "https://")):
        return "https://" + value
    return value


def md_linkify(text: str) -> str:
    """Turn bare URLs inside a markdown string into clickable links."""
    def repl(match: re.Match) -> str:
        url = match.group(0).rstrip(".,;)")
        return f"[{url}]({url})"

    return URL_RE.sub(repl, text or "")


def chips(items: Iterable[Any], tone: str = "") -> str:
    cls = f"cvf-chip cvf-chip--{tone}" if tone else "cvf-chip"
    return "".join(f'<span class="{cls}">{esc(x)}</span>' for x in items if str(x).strip())


def stat_card(label: str, value: Any, hint: str = "") -> str:
    hint_html = f'<div class="cvf-stat__hint">{esc(hint)}</div>' if hint else ""
    return (
        '<div class="cvf-stat">'
        f'<div class="cvf-stat__label">{esc(label)}</div>'
        f'<div class="cvf-stat__value">{esc(value)}</div>'
        f"{hint_html}"
        "</div>"
    )


STATUS_TONES = {
    "completed": "success",
    "generated": "success",
    "ready": "success",
    "draft": "muted",
    "pending": "warning",
    "analyzing": "info",
    "failed": "danger",
    "error": "danger",
}


def status_chip(status: Any) -> str:
    label = str(status or "draft").strip() or "draft"
    tone = STATUS_TONES.get(label.lower(), "muted")
    return f'<span class="cvf-chip cvf-chip--{tone}">{esc(label.replace("_", " ").title())}</span>'


def score_ring(label: str, value: float, suffix: str = "", maximum: float = 100.0) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = 0.0

    ratio = 0.0 if maximum <= 0 else max(0.0, min(1.0, numeric / maximum))
    radius = 46.0
    circumference = 2 * 3.141592653589793 * radius
    offset = circumference * (1 - ratio)

    if ratio >= 0.8:
        colour = "var(--cvf-success)"
    elif ratio >= 0.6:
        colour = "var(--cvf-warning)"
    else:
        colour = "var(--cvf-danger)"

    return (
        '<div class="cvf-ring">'
        '<div class="cvf-ring__chart">'
        f'<svg viewBox="0 0 110 110" width="110" height="110" role="img" '
        f'aria-label="{esc(label)}: {numeric:.1f}{esc(suffix)}">'
        f'<circle cx="55" cy="55" r="{radius}" fill="none" stroke="#e4e7ec" stroke-width="9"/>'
        f'<circle cx="55" cy="55" r="{radius}" fill="none" stroke="{colour}" stroke-width="9" '
        f'stroke-linecap="round" stroke-dasharray="{circumference:.2f}" '
        f'stroke-dashoffset="{offset:.2f}" transform="rotate(-90 55 55)"/>'
        "</svg>"
        f'<span class="cvf-ring__value">{numeric:.1f}{esc(suffix)}</span>'
        "</div>"
        f'<div class="cvf-ring__label">{esc(label)}</div>'
        "</div>"
    )


def page_header(title: str, subtitle: str = "", eyebrow: str = "") -> None:
    parts = ['<div class="cvf-hero">']
    if eyebrow:
        parts.append(f'<div class="cvf-eyebrow">{esc(eyebrow)}</div>')
    parts.append(f'<div class="cvf-title">{esc(title)}</div>')
    if subtitle:
        parts.append(f'<div class="cvf-sub">{subtitle}</div>')
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def stepper(steps: Sequence[str], current: int) -> None:
    """Render a horizontal progress stepper. ``current`` is 1-based."""
    parts = []
    for index, label in enumerate(steps, start=1):
        if index < current:
            state = "done"
            marker = "✓"
        elif index == current:
            state = "active"
            marker = str(index)
        else:
            state = "todo"
            marker = str(index)
        parts.append(
            f'<div class="cvf-step cvf-step--{state}">'
            f'<span class="cvf-step__dot">{marker}</span>'
            f"<span>{esc(label)}</span></div>"
        )
    st.markdown('<div class="cvf-steps">' + "".join(parts) + "</div>", unsafe_allow_html=True)


def empty_state(title: str, body: str) -> None:
    st.markdown(
        f'<div class="cvf-empty"><div class="cvf-empty__title">{esc(title)}</div>'
        f"<div>{esc(body)}</div></div>",
        unsafe_allow_html=True,
    )


def section_label(text: str) -> None:
    st.markdown(f'<div class="cvf-section-title">{esc(text)}</div>', unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Session-local API cache
# --------------------------------------------------------------------------- #

def _invalidate_api_cache(*keys: str) -> None:
    cache = st.session_state.setdefault("api_cache", {})
    if keys:
        for key in keys:
            cache.pop(key, None)
    else:
        cache.clear()


def _cached_workspace_get(
    key: str,
    path: str,
    *,
    ttl: float = 30.0,
) -> Any:
    cache = st.session_state.setdefault("api_cache", {})
    now = time.monotonic()
    entry = cache.get(key)
    if entry and now - float(entry.get("ts", 0)) < ttl:
        return entry.get("data")
    data = get(path, st.session_state.token) or []
    cache[key] = {"ts": now, "data": data}
    return data


def _parallel_workspace_load() -> Tuple[List[Any], List[Any]]:
    with ThreadPoolExecutor(max_workers=2) as pool:
        apps_future = pool.submit(_cached_workspace_get, "applications", "/api/v1/applications")
        profiles_future = pool.submit(_cached_workspace_get, "profiles", "/api/v1/profiles")
        return apps_future.result(), profiles_future.result()


# --------------------------------------------------------------------------- #
# Cached downloads
# --------------------------------------------------------------------------- #

@st.cache_data(show_spinner=False, ttl=600, max_entries=32)
def _cached_download(resume_id: int, fmt: str, version: Any, token: str) -> bytes:
    return download(
        f"/api/v1/resumes/{resume_id}/download",
        token,
        params={"format": fmt},
    )


# --------------------------------------------------------------------------- #
# Authentication
# --------------------------------------------------------------------------- #

FEATURES: Tuple[Tuple[str, str, str], ...] = (
    (
        "🎯",
        "Job intelligence first",
        "Requirements, seniority and domain are extracted before a single line is written.",
    ),
    (
        "🔍",
        "Verified evidence only",
        "Public GitHub repositories and your own answers become the factual basis for every claim.",
    ),
    (
        "✦",
        "Independent Gemini ATS review",
        "Gemini evaluates the finished CV against the user's job description and explains the strongest matches and biggest gaps.",
    ),
)


def login_screen() -> None:
    st.markdown('<div style="height:3vh"></div>', unsafe_allow_html=True)

    left, right = st.columns([1.15, 1], gap="large")

    with left:
        st.markdown(
            '<div class="cvf-hero">'
            '<div class="cvf-eyebrow">Evidence-first resume tailoring</div>'
            '<div class="cvf-title" style="font-size:2.6rem">CVForge</div>'
            '<div class="cvf-sub">Tailor every application to the role without inventing a single '
            "line. CVForge separates job intelligence, verified candidate evidence, generation and "
            "deterministic ATS validation — so the CV you send is one you can defend in the interview."
            "</div></div>",
            unsafe_allow_html=True,
        )
        st.markdown('<div style="height:.6rem"></div>', unsafe_allow_html=True)
        for icon, title, body in FEATURES:
            st.markdown(
                '<div class="cvf-feature">'
                f'<div class="cvf-feature__icon">{icon}</div>'
                "<div>"
                f'<div class="cvf-feature__title">{esc(title)}</div>'
                f'<div class="cvf-feature__body">{esc(body)}</div>'
                "</div></div>",
                unsafe_allow_html=True,
            )

    with right:
        with st.container(border=True):
            st.markdown("#### Welcome")
            st.caption("Sign in, or create an account in a few seconds.")
            tab_in, tab_up = st.tabs(["Sign in", "Create account"])

            with tab_in:
                with st.form("login_form", clear_on_submit=False, border=False):
                    email = st.text_input(
                        "Email",
                        key="login_email",
                        placeholder="you@example.com",
                        autocomplete="email",
                    )
                    password = st.text_input(
                        "Password",
                        type="password",
                        key="login_password",
                        placeholder="••••••••",
                        autocomplete="current-password",
                    )
                    submitted = st.form_submit_button("Sign in", type="primary", **FW)

                if submitted:
                    email = (email or "").strip()
                    if not email or not password:
                        st.error("Enter both your email and password.", icon="🚫")
                    elif not EMAIL_RE.match(email):
                        st.error("That doesn't look like a valid email address.", icon="🚫")
                    else:
                        try:
                            with st.spinner("Signing you in…"):
                                data = auth(
                                    "/api/v1/auth/login",
                                    {"email": email, "password": password},
                                )
                            st.session_state.token = data["token"]
                            st.session_state.user = data.get("user") or {}
                            flash("success", "Signed in. Welcome back.")
                            st.rerun()
                        except (APIError, KeyError) as exc:
                            st.error(str(exc), icon="🚫")

            with tab_up:
                with st.form("register_form", clear_on_submit=False, border=False):
                    name = st.text_input(
                        "Full name", key="reg_name", placeholder="Ada Lovelace"
                    )
                    email = st.text_input(
                        "Email",
                        key="reg_email",
                        placeholder="you@example.com",
                        autocomplete="email",
                    )
                    password = st.text_input(
                        "Password",
                        type="password",
                        key="reg_password",
                        placeholder="At least 8 characters",
                        autocomplete="new-password",
                    )
                    submitted = st.form_submit_button("Create account", type="primary", **FW)

                if submitted:
                    name = (name or "").strip()
                    email = (email or "").strip()
                    problems = []
                    if not name:
                        problems.append("Enter your full name.")
                    if not EMAIL_RE.match(email):
                        problems.append("Enter a valid email address.")
                    if len(password or "") < 8:
                        problems.append("Passwords must be at least 8 characters.")

                    if problems:
                        for problem in problems:
                            st.error(problem, icon="🚫")
                    else:
                        try:
                            with st.spinner("Creating your account…"):
                                data = auth(
                                    "/api/v1/auth/register",
                                    {"name": name, "email": email, "password": password},
                                )
                            st.session_state.token = data["token"]
                            st.session_state.user = data.get("user") or {}
                            flash("success", "Account created. Let's build your first CV.")
                            st.rerun()
                        except (APIError, KeyError) as exc:
                            st.error(str(exc), icon="🚫")


# --------------------------------------------------------------------------- #
# Candidate editor
# --------------------------------------------------------------------------- #

def _candidate_editor(candidate: Dict[str, Any], seq: int) -> Dict[str, Any]:
    """Render the full evidence editor and return the edited candidate."""
    candidate = copy.deepcopy(candidate or {})
    contact = candidate.setdefault("contact", {}) or {}
    candidate["contact"] = contact
    for key in ("experience", "education", "projects", "skills", "certifications"):
        candidate.setdefault(key, [])
    candidate.setdefault("github_repositories", [])

    def key(name: str) -> str:
        return f"c{seq}_{name}"

    tabs = st.tabs(
        ["Personal", "Summary", "Skills", "Experience", "Projects", "Education", "Certifications"]
    )

    # ----- Personal ------------------------------------------------------- #
    with tabs[0]:
        c1, c2 = st.columns(2)
        contact["name"] = c1.text_input(
            "Full name", value=contact.get("name", ""), key=key("name"), placeholder="Ada Lovelace"
        )
        candidate["headline"] = c2.text_input(
            "Professional headline",
            value=candidate.get("headline", ""),
            key=key("headline"),
            placeholder="Data Scientist · Machine Learning · Forecasting",
        )

        c1, c2, c3 = st.columns(3)
        contact["email"] = c1.text_input(
            "Email", value=contact.get("email", ""), key=key("email"), placeholder="you@example.com"
        )
        contact["phone"] = c2.text_input(
            "Phone", value=contact.get("phone", ""), key=key("phone"), placeholder="+91 90000 00000"
        )
        contact["location"] = c3.text_input(
            "Location",
            value=contact.get("location", ""),
            key=key("location"),
            placeholder="Bengaluru, India",
        )

        c1, c2, c3 = st.columns(3)
        contact["linkedin"] = c1.text_input(
            "LinkedIn",
            value=contact.get("linkedin", ""),
            key=key("linkedin"),
            placeholder="https://linkedin.com/in/…",
        )
        contact["github"] = c2.text_input(
            "GitHub",
            value=contact.get("github", ""),
            key=key("github"),
            placeholder="https://github.com/…",
        )
        contact["portfolio"] = c3.text_input(
            "Portfolio",
            value=contact.get("portfolio", ""),
            key=key("portfolio"),
            placeholder="https://…",
        )
        st.caption("Links are preserved and rendered as clickable links in PDF and DOCX exports.")

    # ----- Summary -------------------------------------------------------- #
    with tabs[1]:
        candidate["summary"] = st.text_area(
            "Professional summary",
            value=candidate.get("summary", ""),
            key=key("summary"),
            height=160,
            placeholder="Two to four sentences describing what you do, for whom, and the outcomes you deliver.",
        )
        st.caption(f"{len(candidate['summary'].split())} words")

    # ----- Skills --------------------------------------------------------- #
    with tabs[2]:
        raw_skills = st.text_area(
            "Skills — one per line, or comma separated",
            value="\n".join(candidate.get("skills", [])),
            key=key("skills"),
            height=150,
        )
        candidate["skills"] = [
            item.strip()
            for item in raw_skills.replace(",", "\n").splitlines()
            if item.strip()
        ]
        if candidate["skills"]:
            st.markdown(chips(candidate["skills"]), unsafe_allow_html=True)
        else:
            st.caption("No skills added yet.")

    # ----- Experience ----------------------------------------------------- #
    with tabs[3]:
        experiences = list(candidate.get("experience") or [])
        count_key = key("exp_count")
        minimum = max(3, len(experiences))
        if count_key not in st.session_state:
            st.session_state[count_key] = minimum
        total = max(int(st.session_state[count_key]), minimum)
        experiences = experiences + [{}] * (total - len(experiences))

        edited_experience: List[Dict[str, Any]] = []
        for idx in range(total):
            exp = experiences[idx] or {}
            with st.container(border=True):
                st.markdown(f"**Experience {idx + 1}**")
                c1, c2 = st.columns(2)
                company = c1.text_input(
                    "Company", value=exp.get("company", ""), key=key(f"exp_company_{idx}")
                )
                title = c2.text_input(
                    "Job title", value=exp.get("title", ""), key=key(f"exp_title_{idx}")
                )
                c1, c2, c3 = st.columns(3)
                start = c1.text_input(
                    "Start", value=exp.get("start_date", ""), key=key(f"exp_start_{idx}"),
                    placeholder="Jan 2023",
                )
                end = c2.text_input(
                    "End", value=exp.get("end_date", ""), key=key(f"exp_end_{idx}"),
                    placeholder="Present",
                )
                location = c3.text_input(
                    "Location", value=exp.get("location", ""), key=key(f"exp_location_{idx}")
                )
                bullets = st.text_area(
                    "Achievements — one per line",
                    value="\n".join(exp.get("bullets", []) or []),
                    key=key(f"exp_bullets_{idx}"),
                    height=120,
                    placeholder="Cut reporting time 40% by automating the weekly pipeline in Airflow.",
                )

                if company or title or bullets.strip():
                    edited_experience.append(
                        {
                            "company": company,
                            "title": title,
                            "location": location,
                            "start_date": start,
                            "end_date": end,
                            "bullets": [b.strip(" -•") for b in bullets.splitlines() if b.strip()],
                        }
                    )

        candidate["experience"] = edited_experience
        if st.button("＋ Add another experience", key=key("add_exp")):
            st.session_state[count_key] = total + 1
            st.rerun()
        st.caption("Empty entries are discarded when you generate.")

    # ----- Projects ------------------------------------------------------- #
    with tabs[4]:
        projects = list(candidate.get("projects") or [])
        count_key = key("proj_count")
        minimum = max(4, len(projects))
        if count_key not in st.session_state:
            st.session_state[count_key] = minimum
        total = max(int(st.session_state[count_key]), minimum)
        projects = projects + [{}] * (total - len(projects))

        edited_projects: List[Dict[str, Any]] = []
        for idx in range(total):
            project = projects[idx] or {}
            links = project.get("links") or []
            github_default = next(
                (l.get("url", "") for l in links if l.get("label") == "GitHub"), ""
            )
            demo_default = next(
                (l.get("url", "") for l in links if l.get("label") in {"Live Demo", "Project"}), ""
            )

            with st.container(border=True):
                st.markdown(f"**Project {idx + 1}**")
                name = st.text_input(
                    "Project name",
                    value=project.get("name", ""),
                    key=key(f"proj_name_{idx}"),
                )
                technologies = st.text_input(
                    "Technologies",
                    value=", ".join(project.get("technologies", []) or []),
                    key=key(f"proj_tech_{idx}"),
                    placeholder="Python, FastAPI, PostgreSQL",
                )
                c1, c2 = st.columns(2)
                github = c1.text_input(
                    "GitHub repository",
                    value=github_default,
                    key=key(f"proj_github_{idx}"),
                    placeholder="https://github.com/…",
                )
                demo = c2.text_input(
                    "Live demo / project link",
                    value=demo_default,
                    key=key(f"proj_demo_{idx}"),
                    placeholder="https://…",
                )
                bullets = st.text_area(
                    "Contributions — one per line",
                    value="\n".join(project.get("bullets", []) or []),
                    key=key(f"proj_bullets_{idx}"),
                    height=110,
                )

                if name or bullets.strip() or github.strip() or demo.strip():
                    built_links: List[Dict[str, str]] = []
                    if github.strip():
                        built_links.append({"label": "GitHub", "url": normalise_url(github)})
                    if demo.strip():
                        built_links.append({"label": "Live Demo", "url": normalise_url(demo)})
                    edited_projects.append(
                        {
                            "name": name,
                            "technologies": [t.strip() for t in technologies.split(",") if t.strip()],
                            "bullets": [b.strip(" -•") for b in bullets.splitlines() if b.strip()],
                            "links": built_links,
                            "url": built_links[0]["url"] if built_links else "",
                        }
                    )

        candidate["projects"] = edited_projects
        if st.button("＋ Add another project", key=key("add_proj")):
            st.session_state[count_key] = total + 1
            st.rerun()

    # ----- Education ------------------------------------------------------ #
    with tabs[5]:
        educations = list(candidate.get("education") or [])
        while len(educations) < 2:
            educations.append({})

        edited_education: List[Dict[str, Any]] = []
        for idx in range(len(educations)):
            edu = educations[idx] or {}
            with st.container(border=True):
                st.markdown(f"**Education {idx + 1}**")
                c1, c2 = st.columns(2)
                institution = c1.text_input(
                    "Institution",
                    value=edu.get("institution", ""),
                    key=key(f"edu_inst_{idx}"),
                )
                degree = c2.text_input(
                    "Degree", value=edu.get("degree", ""), key=key(f"edu_degree_{idx}")
                )
                c1, c2, c3 = st.columns(3)
                field = c1.text_input(
                    "Field", value=edu.get("field", ""), key=key(f"edu_field_{idx}")
                )
                start = c2.text_input(
                    "Start", value=edu.get("start_date", ""), key=key(f"edu_start_{idx}")
                )
                end = c3.text_input(
                    "End", value=edu.get("end_date", ""), key=key(f"edu_end_{idx}")
                )
                if institution or degree or field:
                    edited_education.append(
                        {
                            "institution": institution,
                            "degree": degree,
                            "field": field,
                            "location": edu.get("location", ""),
                            "start_date": start,
                            "end_date": end,
                        }
                    )
        candidate["education"] = edited_education

    # ----- Certifications ------------------------------------------------- #
    with tabs[6]:
        candidate["certifications"] = [
            line.strip()
            for line in st.text_area(
                "One certification per line",
                value="\n".join(candidate.get("certifications", []) or []),
                key=key("certs"),
                height=120,
                placeholder="AWS Certified Machine Learning – Specialty",
            ).splitlines()            if line.strip()
        ]

    candidate["github_repositories"] = st.session_state.github_repos
    return candidate


# --------------------------------------------------------------------------- #
# GitHub evidence
# --------------------------------------------------------------------------- #

def inspect_github_repositories(seq: int) -> None:
    st.markdown("##### Verified project evidence")
    st.caption(
        "Paste public GitHub repository URLs — one per line. CVForge reads repository "
        "metadata, README, languages and selected project files. Private repositories are never accessed."
    )

    existing = st.session_state.github_repos or []
    raw = st.text_area(
        "Public GitHub repositories",
        value="\n".join(repo.get("url", "") for repo in existing),
        key=f"c{seq}_github_input",
        height=100,
        label_visibility="collapsed",
        placeholder="https://github.com/owner/project-one\nhttps://github.com/owner/project-two",
    )

    if st.button("Inspect repositories", key=f"c{seq}_github_inspect"):
        urls = [line.strip() for line in raw.splitlines() if line.strip()]
        if not urls:
            st.warning("Add at least one public repository URL.", icon="⚠️")
        else:
            inspected: List[Dict[str, Any]] = []
            progress = st.progress(0.0, text="Inspecting repositories…")
            for index, url in enumerate(urls, start=1):
                try:
                    inspected.append(
                        post("/api/v1/github/inspect", st.session_state.token, json={"url": url})
                    )
                except APIError as exc:
                    if exc.is_auth_error:
                        show_error(exc)
                    st.error(f"{url} — {exc}", icon="🚫")
                progress.progress(index / len(urls), text=f"Inspected {index} of {len(urls)}")
            progress.empty()
            st.session_state.github_repos = inspected
            if inspected:
                st.toast(f"Inspected {len(inspected)} repositories.", icon="✅")

    for repo in st.session_state.github_repos or []:
        with st.container(border=True):
            st.markdown(
                f'<div class="cvf-repo"><div class="cvf-repo__name">'
                f'{esc(repo.get("full_name") or repo.get("name") or "Repository")}</div></div>',
                unsafe_allow_html=True,
            )
            if repo.get("description"):
                st.write(repo["description"])

            meta = [
                str(repo.get("language") or "").strip(),
                ", ".join(repo.get("technologies", []) or []),
                str(repo.get("default_branch") or "").strip(),
            ]
            meta = [m for m in meta if m]
            if meta:
                st.caption(" · ".join(meta))

            if repo.get("technologies"):
                st.markdown(chips(repo["technologies"], tone="muted"), unsafe_allow_html=True)

            if repo.get("readme"):
                with st.expander("Repository evidence"):
                    st.text(str(repo["readme"])[:4000])


# --------------------------------------------------------------------------- #
# Link evidence
# --------------------------------------------------------------------------- #

def collect_link_evidence(candidate: Dict[str, Any], seq: int) -> Dict[str, str]:
    contact = candidate.get("contact") or {}
    projects = candidate.get("projects") or []
    answers: Dict[str, str] = {}

    st.markdown("##### Links & project proof")
    st.caption(
        "Only provide links you actually own or can show as evidence. "
        "CVForge preserves them and makes them clickable in PDF and DOCX exports."
    )

    with st.expander("Professional links", expanded=True):
        c1, c2, c3 = st.columns(3)
        linkedin = c1.text_input(
            "LinkedIn URL",
            value=contact.get("linkedin", ""),
            placeholder="https://linkedin.com/in/your-profile",
            key=f"c{seq}_link_linkedin",
        )
        portfolio = c2.text_input(
            "Portfolio URL",
            value=contact.get("portfolio", ""),
            placeholder="https://yourportfolio.com",
            key=f"c{seq}_link_portfolio",
        )
        github = c3.text_input(
            "GitHub profile",
            value=contact.get("github", ""),
            placeholder="https://github.com/username",
            key=f"c{seq}_link_github",
        )

        if linkedin.strip():
            answers["linkedin_url"] = normalise_url(linkedin)
        if portfolio.strip():
            answers["portfolio_url"] = normalise_url(portfolio)
        if github.strip():
            answers["github_url"] = normalise_url(github)

    with st.expander("Project links", expanded=False):
        st.caption(
            "Per project, provide a name and up to two links. "
            "Typical pair: GitHub plus a live demo."
        )

        for idx, project in enumerate(projects):
            name = st.text_input(
                f"Project {idx + 1} name",
                value=project.get("name", "") or f"Project {idx + 1}",
                key=f"c{seq}_link_project_name_{idx}",
            )
            links = project.get("links") or []
            github_default = next(
                (l.get("url", "") for l in links if l.get("label") == "GitHub"), ""
            )
            demo_default = next(
                (l.get("url", "") for l in links if l.get("label") in {"Live Demo", "Project"}), ""
            )

            c1, c2 = st.columns(2)
            github_url = c1.text_input(
                "GitHub",
                value=github_default,
                placeholder="https://github.com/…",
                key=f"c{seq}_link_project_github_{idx}",
            )
            demo_url = c2.text_input(
                "Live Demo / Portfolio",
                value=demo_default,
                placeholder="https://…",
                key=f"c{seq}_link_project_demo_{idx}",
            )

            if name.strip():
                answers[f"project_name_{idx}"] = name.strip()
            if github_url.strip():
                answers[f"project_github_url_{idx}"] = normalise_url(github_url)
            if demo_url.strip():
                answers[f"project_demo_url_{idx}"] = normalise_url(demo_url)

        st.markdown("**Additional projects**")
        for idx in (1, 2):
            name = st.text_input(
                f"Additional project {idx} name",
                key=f"c{seq}_link_extra_{idx}_name",
                placeholder="Project name",
            )
            c1, c2 = st.columns(2)
            github_url = c1.text_input(
                "GitHub",
                placeholder="https://github.com/…",
                key=f"c{seq}_link_extra_{idx}_github",
            )
            demo_url = c2.text_input(
                "Live Demo / Portfolio",
                placeholder="https://…",
                key=f"c{seq}_link_extra_{idx}_demo",
            )
            if name.strip():
                answers[f"additional_project_{idx}_name"] = name.strip()
            if github_url.strip():
                answers[f"additional_project_{idx}_github_url"] = normalise_url(github_url)
            if demo_url.strip():
                answers[f"additional_project_{idx}_demo_url"] = normalise_url(demo_url)

    st.session_state.link_answers = answers
    return answers


# --------------------------------------------------------------------------- #
# CV Enhance
# --------------------------------------------------------------------------- #

@st.fragment
def new_application() -> None:
    # ------------------------------------------------------------------ #
    # Workspace hero
    # ------------------------------------------------------------------ #
    st.markdown(
        '<div class="cvf-workspace-hero">'
        '<div class="cvf-hero-card">'
        '<div class="cvf-hero-card__eyebrow">CV Enhance · Step 01</div>'
        '<div class="cvf-hero-card__title">Build a CV that is tailored to the role — not a generic template.</div>'
        '<div class="cvf-hero-card__body">'
        'Start with the actual job description. CVForge extracts the role requirements, '
        'combines them with your verified evidence, lets you review everything, then '
        'generates the CV with Groq and independently scores it with Gemini.'
        '</div>'
        '<div class="cvf-model-row">'
        '<span class="cvf-model cvf-model--groq">● Groq · Generate CV</span>'
        '<span class="cvf-model cvf-model--gemini">● Gemini · ATS review</span>'
        '<span class="cvf-model">◆ Evidence-first</span>'
        '</div>'
        '</div>'
        '<div class="cvf-hero-card cvf-hero-card--soft">'
        '<div class="cvf-mini-title">How this works</div>'
        '<div class="cvf-mini-step"><div class="cvf-mini-step__n">1</div>'
        '<div class="cvf-mini-step__body"><strong>Paste the JD</strong><br>We extract role, seniority, domain and required skills.</div></div>'
        '<div class="cvf-mini-step"><div class="cvf-mini-step__n">2</div>'
        '<div class="cvf-mini-step__body"><strong>Confirm evidence</strong><br>Edit your profile and verify public project evidence.</div></div>'
        '<div class="cvf-mini-step"><div class="cvf-mini-step__n">3</div>'
        '<div class="cvf-mini-step__body"><strong>Generate + evaluate</strong><br>Groq builds the CV; Gemini reviews the result.</div></div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    if not st.session_state.analysis:
        current_step = 1
    elif not st.session_state.resume:
        current_step = 2
    else:
        current_step = 3

    stepper(["Target role", "Evidence & profile", "Generated CV"], current_step)

    with st.container(border=False):
        # -------------------------------------------------------------- #
        # Target role intake
        # -------------------------------------------------------------- #
        st.markdown(
            '<div class="cvf-form-shell">'
            '<div class="cvf-form-head">'
            '<div><div class="cvf-form-title">Tell us about the opportunity</div>'
            '<div class="cvf-form-sub">Paste the complete posting for the strongest match.</div></div>'
            '<div class="cvf-step-number">1</div>'
            '</div>',
            unsafe_allow_html=True,
        )

        if hasattr(st, "pills"):
            mode = st.pills(
                "CV workflow",
                ["Enhance existing CV", "Build CV from scratch"],
                default="Enhance existing CV",
                key="cv_mode",
                label_visibility="collapsed",
            )
        else:
            mode = st.radio(
                "CV workflow",
                ["Enhance existing CV", "Build CV from scratch"],
                horizontal=True,
                key="cv_mode",
                label_visibility="collapsed",
            )

        jd = st.text_area(
            "Job description",
            key="jd_input",
            height=250,
            placeholder=(
                "Paste the complete job description…\n\n"
                "Include responsibilities, required skills, qualifications, preferred skills and tools."
            ),
            help="A complete job posting gives Gemini and the generation engine more evidence to work with.",
        )
        jd_words = len((jd or "").split())
        st.caption(f"{jd_words:,} words · {len(jd or ""):,} characters")

        st.markdown(
            '<div class="cvf-upload-card">'
            '<div class="cvf-mini-title">Existing CV <span class="cvf-muted">(optional)</span></div>'
            '<div class="cvf-muted">Upload a PDF, DOCX, TXT or Markdown file. Every extracted field remains editable.</div>',
            unsafe_allow_html=True,
        )
        cv = st.file_uploader(
            "Upload existing CV",
            type=["pdf", "docx", "txt", "md"],
            key="cv_upload",
            label_visibility="collapsed",
            help="Maximum upload size is controlled by the Streamlit deployment.",
        )
        st.markdown("</div>", unsafe_allow_html=True)

        if mode == "Build CV from scratch":
            st.markdown(
                '<div class="cvf-note" style="margin-top:.75rem">'
                '<strong>Starting from zero?</strong> No CV upload is required. '
                'After analysis, CVForge will open the complete evidence editor.'
                '</div>',
                unsafe_allow_html=True,
            )

        c1, c2 = st.columns([1, 1], gap="small")
        with c1:
            analyze = st.button(
                "Analyze job description →",
                type="primary",
                disabled=not jd.strip(),
                key="analyze_button",
                **FW,
            )
        with c2:
            reset = st.button(
                "Clear workspace",
                key="reset_button",
                **FW,
            )

        st.markdown("</div>", unsafe_allow_html=True)

        if reset:
            st.session_state.analysis = None
            st.session_state.resume = None
            st.session_state.application = None
            st.session_state.github_repos = []
            st.session_state.link_answers = {}
            st.session_state.draft_candidate = None
            st.session_state.draft_candidate_seq = None
            st.session_state.form_seq = st.session_state.get("form_seq", 0) + 1
            st.rerun()

    if analyze:
        result: Optional[Dict[str, Any]] = None
        try:
            with st.status("Analyzing the opportunity…", expanded=True) as status:
                st.write("Reading the job description")
                files = (
                    {"cv": (cv.name, cv.getvalue(), cv.type or "application/octet-stream")}
                    if cv is not None
                    else None
                )
                response = request(
                    "POST",
                    "/api/v1/jobs/analyze",
                    token=st.session_state.token,
                    data={"jd": jd},
                    files=files,
                )
                result = response.json()
                st.write("Extracting role and candidate signals")
                status.update(label="Job analysis complete", state="complete")
        except APIError as exc:
            show_error(exc)

        if result:
            st.session_state.analysis = result
            st.session_state.application = None
            st.session_state.resume = None
            st.session_state.github_repos = []
            st.session_state.link_answers = {}
            st.session_state.draft_candidate = None
            st.session_state.draft_candidate_seq = None
            st.session_state.form_seq = st.session_state.get("form_seq", 0) + 1
            flash("success", "Job description analyzed.")
            st.rerun()

    analysis = st.session_state.analysis
    if not analysis:
        st.markdown('<div style="height:.5rem"></div>', unsafe_allow_html=True)
        empty_state(
            "No analysis yet",
            "Paste a job description above and select “Analyze job description” to begin.",
        )
        return

    seq = int(st.session_state.get("form_seq", 0))
    job = analysis.get("job") or {}

    # ----- Step 2: job intelligence --------------------------------------- #
    with st.container(border=True):
        st.markdown("#### 2 · Job intelligence")
        columns = st.columns(4)
        columns[0].markdown(
            stat_card("Role family", str(job.get("role_family", "general")).replace("_", " ").title()),
            unsafe_allow_html=True,
        )
        columns[1].markdown(
            stat_card("Seniority", str(job.get("seniority", "entry")).title()), unsafe_allow_html=True
        )
        columns[2].markdown(
            stat_card("Domain", str(job.get("domain", "general")).title()), unsafe_allow_html=True
        )
        columns[3].markdown(
            stat_card("Required skills", len(job.get("must_have_skills", []) or [])),
            unsafe_allow_html=True,
        )

        must_have = job.get("must_have_skills") or []
        if must_have:
            st.markdown('<div style="height:.6rem"></div>', unsafe_allow_html=True)
            st.markdown(chips(must_have), unsafe_allow_html=True)

        nice_to_have = job.get("nice_to_have_skills") or []
        if nice_to_have:
            st.markdown(chips(nice_to_have, tone="muted"), unsafe_allow_html=True)

    # ----- Step 3: candidate profile -------------------------------------- #
    st.markdown('<hr class="cvf-divider"/>', unsafe_allow_html=True)
    page_header(
        "Your profile",
        "Correct or complete the extracted information. Everything here becomes evidence for generation.",
        eyebrow="Step 3",
    )
    candidate = _candidate_editor(analysis.get("candidate") or {}, seq)

    # ----- Step 4: evidence ----------------------------------------------- #
    st.markdown('<hr class="cvf-divider"/>', unsafe_allow_html=True)
    page_header(
        "Evidence",
        "Strengthen the factual basis for your CV with verified public repositories and direct answers.",
        eyebrow="Step 4",
    )
    inspect_github_repositories(seq)
    candidate["github_repositories"] = st.session_state.github_repos

    answers: Dict[str, str] = {}

    questions = analysis.get("questions") or []
    if questions:
        st.markdown("##### Evidence questions")
        st.caption("Answer only what is true. These answers become additional evidence for generation.")
        for question in questions:
            q_key = question.get("key")
            if not q_key:
                continue
            answers[q_key] = st.text_area(
                question.get("question", ""),
                help=question.get("reason", ""),
                key=f"c{seq}_q_{q_key}",
            )

    answers.update(collect_link_evidence(candidate, seq))

    # ----- Step 5: generate ----------------------------------------------- #
    st.markdown('<hr class="cvf-divider"/>', unsafe_allow_html=True)
    with st.container(border=True):
        c1, c2 = st.columns([2, 1])
        with c1:
            st.markdown("#### 5 · Generate tailored CV")
            st.caption(
                "Groq builds the tailored CV from your evidence. Gemini then independently evaluates "
                "the finished CV against the job description and explains the match."
            )
        with c2:
            generate = st.button(
                "Generate tailored CV",
                type="primary",
                key="generate_button",
                **FW,
            )

    if generate:
        try:
            with st.spinner("Saving your application…"):
                created = post(
                    "/api/v1/jobs/applications",
                    st.session_state.token,
                    json={"job": job, "candidate": candidate},
                )
            st.session_state.application = created

            with st.spinner(
                "Building your CV with Groq, then running an independent Gemini ATS review…"
            ):
                result = post(
                    f"/api/v1/jobs/applications/{created['id']}/generate",
                    st.session_state.token,
                    json=answers,
                )

            st.session_state.resume = result
            _invalidate_api_cache("applications")
            st.toast("CV generated successfully.", icon="✅")
        except APIError as exc:
            show_error(exc)

    if st.session_state.resume:
        render_resume(st.session_state.resume)


# --------------------------------------------------------------------------- #
# Resume rendering
# --------------------------------------------------------------------------- #

def render_resume(result: Dict[str, Any]) -> None:
    resume = result.get("resume") or {}
    ats = result.get("ats") or {}
    resume_id = result.get("resume_id")
    version = result.get("version")

    st.markdown('<hr class="cvf-divider"/>', unsafe_allow_html=True)

    head_left, head_right = st.columns([3, 2])
    with head_left:
        page_header(
            "Your tailored CV",
            "Generated by Groq and independently evaluated by Gemini against the exact job description.",
            eyebrow="Result",
        )
    with head_right:
        if resume_id:
            b1, b2 = st.columns(2)
            for column, fmt, label, mime in (
                (b1, "pdf", "Download PDF", "application/pdf"),
                (b2, "docx", "Download DOCX", DOCX_MIME),
            ):
                try:
                    payload = _cached_download(
                        int(resume_id), fmt, version, str(st.session_state.token or "")
                    )
                    column.download_button(
                        label,
                        payload,
                        file_name=f"cvforge_resume_{resume_id}.{fmt}",
                        mime=mime,
                        key=f"dl_{fmt}_{resume_id}_{version}",
                        **FW,
                    )
                except APIError:
                    column.caption(f"{label} unavailable")

    # ----- ATS evaluation ------------------------------------------------ #
    score = float(ats.get("score", 0) or 0)
    if score >= 85:
        verdict = ("Excellent match", "The CV is strongly aligned with this role.")
    elif score >= 75:
        verdict = ("Strong match", "The CV is well aligned with a few targeted improvements.")
    elif score >= 60:
        verdict = ("Competitive match", "The CV is relevant, but several signals can be strengthened.")
    else:
        verdict = ("Needs improvement", "Important job signals are currently weak or missing.")

    with st.container(border=True):
        score_rows = [
            ("ATS score", score, "", 100.0),
            ("Keyword coverage", ats.get("keyword_coverage", 0), "%", 100.0),
            ("Required skills", ats.get("required_skill_coverage", 0), "%", 100.0),
            ("Responsibility match", ats.get("responsibility_alignment", 0), "%", 100.0),
        ]
        st.markdown(
            '<div class="cvf-ring-row">'
            + "".join(score_ring(*row) for row in score_rows)
            + "</div>",
            unsafe_allow_html=True,
        )

        st.markdown(
            f"**{esc(verdict[0])}**  
"
            f"<span class='cvf-muted'>{esc(verdict[1])}</span>",
            unsafe_allow_html=True,
        )

        c1, c2 = st.columns(2)
        c1.markdown(
            stat_card(
                "Title alignment",
                f"{float(ats.get('title_alignment', 0) or 0):.1f}%",
                "Role/headline alignment.",
            ),
            unsafe_allow_html=True,
        )
        c2.markdown(
            stat_card(
                "Formatting score",
                f"{float(ats.get('formatting_score', 0) or 0):.1f}%",
                "Gemini machine-readability assessment.",
            ),
            unsafe_allow_html=True,
        )

    with st.container(border=True):
        st.markdown("#### Gemini ATS review")
        st.caption(
            "Gemini evaluated the generated CV against the job signals extracted from the user's job description."
        )

        matched = ats.get("matched_keywords") or []
        missing = ats.get("missing_keywords") or []
        strengths = ats.get("strengths") or []
        gaps = ats.get("gaps") or []
        recommendations = ats.get("recommendations") or []

        c1, c2 = st.columns(2, gap="large")
        with c1:
            st.markdown("**What is working**")
            if strengths:
                for item in strengths:
                    st.markdown(f"- {esc(item)}")
            else:
                st.caption("No strengths were returned.")

        with c2:
            st.markdown("**What needs attention**")
            if gaps:
                for item in gaps:
                    st.markdown(f"- {esc(item)}")
            else:
                st.caption("No major gaps were returned.")

        if matched:
            st.markdown("**Matched signals**")
            st.markdown(chips(matched, tone="success"), unsafe_allow_html=True)

        if missing:
            st.markdown("**Missing or weak signals**")
            st.markdown(chips(missing, tone="warning"), unsafe_allow_html=True)

        if recommendations:
            with st.expander("Highest-impact recommendations", expanded=True):
                for item in recommendations:
                    st.markdown(f"- {esc(item)}")

    for warning in ats.get("warnings") or []:
        st.warning(str(warning), icon="⚠️")

    # ----- Preview -------------------------------------------------------- #
    with st.container(border=True):
        if resume.get("name"):
            st.markdown(
                f'<div class="cvf-resume-name">{esc(resume["name"])}</div>',
                unsafe_allow_html=True,
            )
        if resume.get("headline"):
            st.markdown(
                f'<div class="cvf-headline">{esc(resume["headline"])}</div>',
                unsafe_allow_html=True,
            )
        if resume.get("contact_line"):
            st.markdown(md_linkify(str(resume["contact_line"])))

        professional_links = resume.get("professional_links") or []
        if professional_links:
            st.markdown(
                " · ".join(
                    f"[{esc(link.get('label', 'Link'))}]({normalise_url(link.get('url', ''))})"
                    for link in professional_links
                    if link.get("url")
                )
            )

        if resume.get("summary"):
            st.write(resume["summary"])

        # Skills
        skill_groups = resume.get("skill_groups") or {}
        skills = resume.get("skills") or []
        if skill_groups or skills:
            section_label("Skills")
            if skill_groups:
                for group, values in skill_groups.items():
                    if values:
                        st.markdown(f"**{esc(group)}:** {esc(', '.join(str(v) for v in values))}")
            else:
                st.markdown(chips(skills), unsafe_allow_html=True)

        # Experience
        experience = resume.get("experience") or []
        if experience:
            section_label("Experience")
            for item in experience:
                title = esc(item.get("title", ""))
                company = esc(item.get("company", ""))
                st.markdown(f"**{title}** — {company}")
                if item.get("dates"):
                    st.caption(str(item["dates"]))
                for bullet in item.get("bullets", []) or []:
                    st.markdown(f"- {bullet}")

        # Projects
        projects = resume.get("projects") or []
        if projects:
            section_label("Projects")
            for project in projects:
                st.markdown(f"**{esc(project.get('name', ''))}**")
                links = project.get("links") or []
                if links:
                    st.markdown(
                        " · ".join(
                            f"[{esc(link.get('label', 'Project'))}]"
                            f"({normalise_url(link.get('url', ''))})"
                            for link in links
                            if link.get("url")
                        )
                    )
                elif project.get("url"):
                    st.markdown(f"[Project link]({normalise_url(project['url'])})")
                if project.get("technologies"):
                    st.caption(", ".join(str(t) for t in project["technologies"]))
                for bullet in project.get("bullets", []) or []:
                    st.markdown(f"- {bullet}")

        # Education
        education = resume.get("education") or []
        if education:
            section_label("Education")
            for item in education:
                degree = esc(item.get("degree", ""))
                field = esc(item.get("field", ""))
                institution = esc(item.get("institution", ""))
                st.markdown(f"**{degree} {field}** — {institution} {esc(item.get('dates', ''))}")

        # Certifications
        certifications = resume.get("certifications") or []
        if certifications:
            section_label("Certifications")
            st.markdown(chips(certifications, tone="muted"), unsafe_allow_html=True)

    # ----- Editing -------------------------------------------------------- #
    with st.expander("Edit resume and save a new revision"):
        st.info(
            "Saving an edited revision will run Gemini ATS evaluation again, so the score stays aligned with the exact CV version you save.",
            icon="✦",
        )
        edited = copy.deepcopy(resume)

        edited["contact_line"] = st.text_input(
            "Contact line",
            value=resume.get("contact_line", ""),
            key=f"edit_contact_{resume_id}_{version}",
        )
        edited["headline"] = st.text_input(
            "Headline",
            value=resume.get("headline", ""),
            key=f"edit_headline_{resume_id}_{version}",
        )
        edited["summary"] = st.text_area(
            "Summary",
            value=resume.get("summary", ""),
            height=160,
            key=f"edit_summary_{resume_id}_{version}",
        )
        edited["skills"] = [
            item.strip()
            for item in st.text_input(
                "Skills (comma separated)",
                value=", ".join(resume.get("skills", []) or []),
                key=f"edit_skills_{resume_id}_{version}",
            ).split(",")
            if item.strip()
        ]

        if edited.get("projects"):
            st.caption("Project links")
            for idx, project in enumerate(edited["projects"]):
                links = project.get("links") or []
                github_default = next(
                    (l.get("url", "") for l in links if l.get("label") == "GitHub"), ""
                )
                demo_default = next(
                    (l.get("url", "") for l in links if l.get("label") in {"Live Demo", "Project"}),
                    "",
                )
                c1, c2 = st.columns(2)
                github = c1.text_input(
                    f"{project.get('name', 'Project')} — GitHub",
                    value=github_default,
                    key=f"edit_proj_github_{resume_id}_{version}_{idx}",
                )
                demo = c2.text_input(
                    f"{project.get('name', 'Project')} — Live Demo",
                    value=demo_default,
                    key=f"edit_proj_demo_{resume_id}_{version}_{idx}",
                )

                rebuilt: List[Dict[str, str]] = []
                if github.strip():
                    rebuilt.append({"label": "GitHub", "url": normalise_url(github)})
                if demo.strip():
                    rebuilt.append({"label": "Live Demo", "url": normalise_url(demo)})
                edited["projects"][idx]["links"] = rebuilt
                edited["projects"][idx]["url"] = rebuilt[0]["url"] if rebuilt else ""

        if st.button("Save new revision", key=f"save_revision_{resume_id}_{version}"):
            if not resume_id:
                st.error("This resume has no saved identifier yet.", icon="🚫")
            else:
                try:
                    with st.spinner("Saving revision…"):
                        saved = put(
                            f"/api/v1/resumes/{resume_id}",
                            st.session_state.token,
                            json={"resume": edited},
                        )
                    _cached_download.clear()
                    st.session_state.resume = {
                        **result,
                        "resume_id": saved.get("id", resume_id),
                        "version": saved.get("version", version),
                        "resume": saved.get("resume", edited),
                        "ats": saved.get("ats", ats),
                    }
                    flash("success", f"Saved revision v{saved.get('version', '?')}.")
                    st.rerun()
                except APIError as exc:
                    show_error(exc)


# --------------------------------------------------------------------------- #
# Applications
# --------------------------------------------------------------------------- #

@st.fragment
def applications() -> None:
    page_header(
        "Applications",
        "Every role you have analyzed, and the CV revisions generated for it.",
        eyebrow="Workspace",
    )

    try:
        with st.spinner("Loading applications…"):
            rows = _cached_workspace_get("applications", "/api/v1/applications")
    except APIError as exc:
        show_error(exc)
        return

    if not rows:
        empty_state(
            "No applications yet",
            "Start with a job description and CVForge will build the rest.",
        )
        st.markdown('<div style="height:.6rem"></div>', unsafe_allow_html=True)
        if st.button("✨ Start a new application", type="primary", key="apps_empty_start"):
            st.session_state.page = "CV Studio"
            st.rerun()
        return

    search = st.text_input(
        "Search applications",
        placeholder="Filter by role or company…",
        label_visibility="collapsed",
        key="app_search",
    ).strip().lower()

    filtered = [
        row
        for row in rows
        if not search
        or search in str(row.get("job_title", "")).lower()
        or search in str(row.get("company", "")).lower()
    ]

    st.caption(f"{len(filtered)} of {len(rows)} applications")

    if not filtered:
        empty_state("No matches", "Try a different search term.")
        return

    for row in filtered:
        with st.container(border=True):
            c1, c2, c3 = st.columns([4, 1.2, 1])
            with c1:
                st.markdown(f"**{esc(row.get('job_title') or 'Untitled role')}**")
                if row.get("company"):
                    st.caption(str(row["company"]))
            with c2:
                st.markdown(status_chip(row.get("status", "draft")), unsafe_allow_html=True)
            with c3:
                if st.button("Open", key=f"open_app_{row['id']}", **FW):
                    try:
                        detail = get(
                            f"/api/v1/applications/{row['id']}", st.session_state.token
                        )
                        resumes = (detail or {}).get("resumes") or []
                        if resumes:
                            latest = resumes[0]
                            st.session_state.resume = {
                                "resume_id": latest.get("id"),
                                "version": latest.get("version"),
                                "resume": latest.get("resume") or {},
                                "ats": latest.get("ats") or {},
                            }
                            st.session_state.page = "CV Studio"
                            st.rerun()
                        else:
                            st.info("No resume has been generated for this application yet.")
                    except APIError as exc:
                        show_error(exc)


# --------------------------------------------------------------------------- #
# Profiles
# --------------------------------------------------------------------------- #

@st.fragment
def profiles() -> None:
    page_header(
        "Candidate profiles",
        "Save reusable evidence profiles so you never re-upload the same CV twice.",
        eyebrow="Workspace",
    )

    try:
        with st.spinner("Loading profiles…"):
            rows = _cached_workspace_get("profiles", "/api/v1/profiles")
    except APIError as exc:
        show_error(exc)
        return

    if rows:
        for profile in rows:
            with st.container(border=True):
                st.markdown(f"**{esc(profile.get('name', 'Untitled profile'))}**")
                with st.expander("Profile data"):
                    st.json(profile.get("profile") or {})
    else:
        empty_state(
            "No saved profiles",
            "Analyze a CV, then save the extracted evidence here for reuse.",
        )

    st.markdown('<hr class="cvf-divider"/>', unsafe_allow_html=True)
    st.markdown("#### Save a profile from the current analysis")

    analysis = st.session_state.analysis
    if not analysis:
        st.info(
            "Analyze a job description first — the extracted candidate evidence can then be saved here.",
            icon="ℹ️",
        )
        if st.button("✨ Go to CV Enhance", type="primary", key="profiles_goto"):
            st.session_state.page = "CV Enhance"
            st.rerun()
        return

    name = st.text_input("Profile name", value="My CV", key="profile_name")
    if st.button("Save current candidate profile", type="primary", key="save_profile"):
        if not name.strip():
            st.error("Give the profile a name.", icon="🚫")
        else:
            try:
                with st.spinner("Saving profile…"):
                    result = post(
                        "/api/v1/profiles/manual",
                        st.session_state.token,
                        params={"name": name.strip()},
                        json=analysis.get("candidate") or {},
                    )
                flash("success", f"Saved profile #{result.get('id', '')}.")
                st.rerun()
            except APIError as exc:
                show_error(exc)


# --------------------------------------------------------------------------- #
# Overview
# --------------------------------------------------------------------------- #

@st.fragment
def dashboard() -> None:
    user = st.session_state.user or {}
    first_name = (user.get("name") or "").strip().split(" ")[0]
    greeting = f"Welcome back, {first_name}" if first_name else "Welcome back"

    page_header(
        greeting,
        "A faster workspace for tailoring applications, reviewing ATS alignment, and reusing verified evidence.",
        eyebrow="Dashboard",
    )

    try:
        with st.spinner("Loading workspace…"):
            apps, profs = _parallel_workspace_load()
    except APIError as exc:
        show_error(exc)
        return

    completed = sum(1 for a in apps if str(a.get("status", "")).lower() == "completed")
    in_progress = sum(1 for a in apps if str(a.get("status", "")).lower() not in {"completed", "failed"})

    columns = st.columns(4)
    columns[0].markdown(stat_card("Applications", len(apps), "Total analyzed"), unsafe_allow_html=True)
    columns[1].markdown(stat_card("Completed", completed, "Fully generated"), unsafe_allow_html=True)
    columns[2].markdown(stat_card("In progress", in_progress, "Awaiting generation"), unsafe_allow_html=True)
    columns[3].markdown(stat_card("Saved profiles", len(profs), "Reusable evidence"), unsafe_allow_html=True)

    st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)

    # ----- Quick actions -------------------------------------------------- #
    st.markdown("#### Quick actions")
    q1, q2, q3 = st.columns(3)
    if q1.button("✨ Tailor a new CV", type="primary", key="qa_new", **FW):
        st.session_state.page = "CV Enhance"
        st.rerun()
    if q2.button("🗂️ Review applications", key="qa_apps", **FW):
        st.session_state.page = "Applications"
        st.rerun()
    if q3.button("👤 Manage profiles", key="qa_profiles", **FW):
        st.session_state.page = "Profiles"
        st.rerun()

    st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)

    left, right = st.columns([3, 2], gap="large")

    with left:
        st.markdown("#### Recent applications")
        if not apps:
            empty_state("Nothing here yet", "Your generated applications will appear in this list.")
        else:
            for row in apps[:5]:
                with st.container(border=True):
                    c1, c2 = st.columns([4, 1.4])
                    with c1:
                        st.markdown(f"**{esc(row.get('job_title') or 'Untitled role')}**")
                        if row.get("company"):
                            st.caption(str(row["company"]))
                    with c2:
                        st.markdown(
                            status_chip(row.get("status", "draft")), unsafe_allow_html=True
                        )

    with right:
        st.markdown("#### How CVForge works")
        st.markdown(
            '<div class="cvf-stat" style="gap:.6rem">'
            '<div class="cvf-stat__label">Evidence-first workflow</div>'
            '<div style="font-size:.9rem;line-height:1.6;color:var(--cvf-muted)">'
            "CVForge separates <strong>job intelligence</strong>, <strong>candidate evidence</strong>, "
            "<strong>prompt selection</strong>, <strong>generation</strong> and "
            "<strong>deterministic ATS validation</strong>.<br><br>"
            "The model rewrites evidence — it does not invent it. Every claim in your CV traces back "
            "to something you supplied."
            "</div></div>",
            unsafe_allow_html=True,
        )


# --------------------------------------------------------------------------- #
# Shell
# --------------------------------------------------------------------------- #

def sidebar() -> None:
    user = st.session_state.user or {}
    name = (user.get("name") or "Account").strip() or "Account"
    email = (user.get("email") or "").strip()
    initial = (name[:1] or "?").upper()

    with st.sidebar:
        st.markdown(
            '<div class="cvf-brand">'
            '<div class="cvf-brand__mark">CV</div>'
            "<div>"
            '<div class="cvf-brand__name">CVForge</div>'
            '<div class="cvf-brand__tag">Evidence-first tailoring</div>'
            "</div></div>",
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="cvf-user">'
            f'<div class="cvf-user__avatar">{esc(initial)}</div>'
            '<div class="cvf-user__body">'
            f'<div class="cvf-user__name">{esc(name)}</div>'
            f'<div class="cvf-user__mail">{esc(email)}</div>'
            "</div></div>",
            unsafe_allow_html=True,
        )

        current = st.session_state.get("page", "Dashboard")
        if current not in {label for label, _ in NAV_ITEMS}:
            current = "Dashboard"
            st.session_state.page = current

        for label, icon in NAV_ITEMS:
            active = current == label
            if st.button(
                f"{icon}  {label}",
                key=f"nav_{label}",
                type="primary" if active else "secondary",
                **FW,
            ):
                st.session_state.page = label
                st.rerun()

        st.markdown(
            '<div style="margin:.8rem 0">'
            '<div class="cvf-muted" style="font-size:.7rem;margin-bottom:.35rem">QUICK ACTION</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        if st.button("✦  Create tailored CV", key="sidebar_create_cv", type="primary", **FW):
            st.session_state.page = "CV Studio"
            st.rerun()

        st.divider()
        st.markdown(
            f'<div class="cvf-muted" style="font-size:.72rem;word-break:break-all">'
            f"API · {esc(API_URL)}</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="cvf-muted" style="font-size:.68rem;margin-top:.3rem">'
            f'{esc(UI_BUILD)} · Groq build · Gemini review</div>',
            unsafe_allow_html=True,
        )

        if st.button("↩︎  Sign out", key="sign_out", **FW):
            reset_session()
            flash("info", "You have been signed out.")
            st.rerun()


def main() -> None:
    render_flash()

    if not st.session_state.token:
        login_screen()
        return

    sidebar()

    page = st.session_state.get("page", "Overview")
    if page == "Dashboard":
        dashboard()
    elif page == "CV Studio":
        new_application()
    elif page == "Applications":
        applications()
    elif page == "Profiles":
        profiles()
    else:
        st.session_state.page = "Dashboard"
        dashboard()


main()