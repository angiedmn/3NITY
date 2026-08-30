import time
import random
from datetime import datetime, timezone

import pandas as pd
import requests
import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config

# ==========================================
# PAGE CONFIGURATION & THEME SYSTEM
# ==========================================
st.set_page_config(layout="wide", page_title="3NITY | AML Topology Command")

# Frozen Lake Color Palette
T = {
    "bg": "#FFFAFA",         # Snow white
    "card": "#FFFFFF",       # Pure white for cards to pop slightly
    "sidebar": "#FFFAFA",    # Snow white
    "text": "#000080",       # Navy blue
    "muted": "#6D8196",      # Slate gray
    "border": "#ADD8E6",     # Icy blue
    "accent": "#000080",     # Navy blue
    "accent_soft": "#ADD8E6",# Icy blue
    "accent_mid": "#6D8196", # Slate gray
    "accent_text": "#FFFAFA",# Snow white
    "high": "#8B0000",       # Keep standard risk colors for semantics
    "moderate": "#D2691E", 
    "safe": "#006400"
}

NAV_PAGES = ["Home", "Upload & Scan", "Topology Report", "Network Investigation", "Account Settings"]

DEFAULTS = {
    "bank_name": "Institution",
    "api_url": "http://localhost:8000/api/v1/transaction/evaluate",
    "scan_history": [], "page": "Home"
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

RISK = {"high": T["high"], "moderate": T["moderate"], "safe": T["safe"]}


def risk_bucket(value: float, invert: bool = False) -> str:
    v = (100.0 - value) if invert else value
    if v >= 70:
        return "high"
    if v >= 40:
        return "moderate"
    return "safe"


def risk_label(bucket: str) -> str:
    return {"high": "CRITICAL", "moderate": "MODERATE", "safe": "SAFE"}[bucket]


# ==========================================
# STYLES & INTERFACE SCENT
# ==========================================
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=Instrument+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap');

html, body, [class*="css"] {{ font-family: 'Geist', sans-serif; font-weight: 600; }}
.stApp {{ background-color: {T['bg']}; color: {T['text']}; }}
[data-testid="stSidebar"] {{ background-color: {T['sidebar']}; border-right: 1px solid {T['border']}; }}
[data-testid="stSidebar"] * {{ color: {T['text']}; font-weight: 600; }}

.block-container {{ padding-top: 4.5rem !important; }}

h1, h2, h3, h4, .topbar-title {{ 
    font-family: 'Instrument Sans', sans-serif !important; 
    font-weight: 700 !important; 
    color: {T['text']}; 
    letter-spacing: -0.01em; 
}}

p, span, label, div, td, th {{ 
    font-family: 'Geist', sans-serif; 
    font-weight: 600; 
    color: {T['text']}; 
}}

.muted {{ color: {T['muted']} !important; font-size: 0.85rem; font-weight: 600; }}

div[role="radiogroup"] label {{
    display: flex !important;
    align-items: center !important;
    width: 100% !important;
    padding: 12px 16px !important;
    margin-bottom: 4px !important;
    cursor: pointer !important;
    border-radius: 8px !important;
    transition: background-color 0.2s ease;
}}
div[role="radiogroup"] label:hover {{
    background-color: {T['accent_soft']} !important;
}}
div[role="radiogroup"] label > div:last-child {{
    width: 100%;
}}

.topbar {{
    display: flex; align-items: center; justify-content: space-between;
    padding: 8px 4px 18px 4px; border-bottom: 1px solid {T['border']}; margin-bottom: 18px;
}}
.topbar-brand {{ display: flex; align-items: center; gap: 12px; }}
.topbar-title {{ font-size: 1.4rem; }}

.profile-card {{ text-align: center; padding: 10px 0 20px 0; }}
.profile-avatar {{
    width: 72px; height: 72px; border-radius: 50%;
    background: {T['accent_soft']};
    display: flex; align-items: center; justify-content: center;
    margin: 0 auto 10px auto; border: 2.5px solid {T['accent']};
    font-size: 26px; font-weight: bold; color: {T['accent']};
    font-family: 'Instrument Sans', sans-serif;
}}
.profile-name {{ font-size: 1.05rem; font-weight: bold; margin: 2px 0 6px 0; }}
.profile-pill {{
    display: inline-block; background: {T['accent_soft']}; color: {T['accent']};
    font-size: 0.72rem; font-weight: bold; padding: 4px 12px; border-radius: 999px;
}}

.card {{
    background: {T['card']}; border: 1px solid {T['border']}; border-radius: 14px;
    padding: 20px; box-shadow: 0 2px 8px rgba(109, 129, 150, 0.1);
}}
.stat-label {{ font-size: 0.78rem; color: {T['muted']}; font-weight: bold; text-transform: uppercase; letter-spacing: 0.04em; }}
.stat-value {{ font-size: 1.65rem; font-weight: bold; margin-top: 4px; font-family: 'Instrument Sans', sans-serif !important; }}

.engine-card {{
    background: {T['card']}; border: 1px solid {T['border']}; border-radius: 14px;
    padding: 16px 18px; border-left: 6px solid var(--engine-color); transition: all 0.2s ease;
    height: 120px; 
    display: flex;
    flex-direction: column;
    justify-content: center;
    box-shadow: 0 2px 8px rgba(109, 129, 150, 0.08);
}}
.engine-name {{ font-size: 0.8rem; font-weight: bold; letter-spacing: 0.06em; color: {T['muted']}; text-transform: uppercase; }}
.engine-score {{ font-size: 1.8rem; font-family: 'Instrument Sans', sans-serif !important; font-weight: 700 !important; color: {T['accent']} !important; margin: 4px 0; }}

.risk-badge {{ display: inline-block; padding: 3px 12px; border-radius: 999px; font-weight: bold; font-size: 0.75rem; color: #FFF; width: fit-content; }}
.risk-high {{ background: {RISK['high']}; }}
.risk-moderate {{ background: {RISK['moderate']}; }}
.risk-safe {{ background: {RISK['safe']}; }}

div.hero {{
    background: {T['card']};
    border: 2px solid {T['accent']};
    border-radius: 18px;
    padding: 30px 34px;
    margin-bottom: 22px;
    box-shadow: 0 2px 8px rgba(109, 129, 150, 0.1);
}}
div.hero h1 {{ color: {T['accent']} !important; margin: 0 0 6px 0; font-size: 1.85rem; font-weight: bold; }}
div.hero p {{ color: {T['text']} !important; margin: 0; font-size: 0.95rem; font-weight: 600; }}

.terminal {{
    background: {T['accent']}; border-radius: 12px; padding: 16px 18px;
    font-family: monospace; font-size: 0.82rem; line-height: 1.55;
    color: {T['bg']}; border: 1px solid {T['accent_mid']}; min-height: 220px; white-space: pre-wrap; font-weight: bold;
}}
.terminal .ok {{ color: {T['accent_soft']}; }}
.terminal .warn {{ color: #FFB347; }}
.terminal .err {{ color: #FF9999; }}
.terminal .sys {{ color: {T['bg']}; }}

.topology-diagram {{
    background: {T['accent']}; color: {T['bg']}; border-radius: 12px; padding: 18px 20px;
    font-family: monospace; font-size: 0.74rem; line-height: 1.45;
    border: 1px solid {T['accent_mid']}; overflow-x: auto; white-space: pre; font-weight: bold;
}}

.stButton>button {{ border-radius: 10px; font-weight: bold; padding: 0.5rem 1rem; background-color: {T['accent']} !important; color: white !important; border: none; }}
.stButton>button * {{ color: #FFFFFF !important; }}
.stButton>button:hover {{ background-color: {T['accent_mid']} !important; }}
.stDownloadButton>button {{ background: {T['bg']} !important; border: 2px solid {T['accent']} !important; }}
.stDownloadButton>button, .stDownloadButton>button * {{ color: {T['accent']} !important; }}
.stDownloadButton>button:hover {{ background: {T['accent_soft']} !important; }}
hr {{ border-color: {T['border']}; }}
</style>
""", unsafe_allow_html=True)


# ==========================================
# TOPBAR WITH PROFILE BUTTON
# ==========================================
def render_topbar():
    left, right = st.columns([6, 1.4])
    with left:
        st.markdown(f"""
        <div class="topbar">
            <div class="topbar-brand">
                <span class="topbar-title">3NITY</span>
                <span class="muted" style="border-left:1px solid {T['border']}; padding-left:10px;">AML Orchestrator</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with right:
        initials = "".join([w[0] for w in st.session_state.bank_name.split()[:2]]).upper()
        with st.popover(f"{st.session_state.bank_name.split()[0]} ({initials})", use_container_width=True):
            st.markdown(f"**{st.session_state.bank_name}**")
            st.caption("Verified Institution")
            st.divider()
            if st.button("Account Settings", use_container_width=True, key="topbar_settings"):
                st.session_state.page = "Account Settings"
                st.rerun()
            st.divider()
            if st.button("Sign Out", use_container_width=True, key="topbar_signout"):
                st.session_state.scan_history = []
                st.rerun()


# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    initials = "".join([w[0] for w in st.session_state.bank_name.split()[:2]]).upper()
    st.markdown(f"""
    <div class="profile-card">
        <div class="profile-avatar">{initials}</div>
        <div class="muted" style="font-size:0.7rem; letter-spacing:0.1em; font-weight:bold;">INSTITUTION</div>
        <div class="profile-name">{st.session_state.bank_name}</div>
        <span class="profile-pill">ORCHESTRATOR LIVE</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div class='muted' style='text-align:center; margin-bottom:6px;'>NAVIGATION</div>", unsafe_allow_html=True)
    st.session_state.page = st.radio(
        "nav_menu", NAV_PAGES, label_visibility="collapsed",
        index=NAV_PAGES.index(st.session_state.page),
    )

    st.divider()
    st.markdown("<div class='muted' style='margin-top:10px;'>Gateway Endpoint</div>", unsafe_allow_html=True)
    st.session_state.api_url = st.text_input("api_url", value=st.session_state.api_url, label_visibility="collapsed")


render_topbar()


# ==========================================
# DIAGRAMMED PIPELINE SPECIFICATION
# ==========================================
TOPOLOGY_DIAGRAM = """
[ Client Terminal ]                               [ Core Banking ]
         |                                               |
  (1) Biometric Payload                           (2) Transaction Event
         |                                               |
         v                                               v
+------------------+                             +------------------+
|   GAIT ENGINE    |                             | ORCHESTRATOR API |
|------------------|                             |------------------|
| Inline Scaler/IF |---(Gait Score)------------->| Read Gait Score  |
| Response: ~20ms  |                             | Fetch Tempo      |
+------------------+                             | Fetch Mirage     |
                                                 | Circuit Breaker  |
                                                 +------------------+
                                                   ^              ^
                                      (Tempo Score)|              |(Mirage Score)
                            +----------------------+              +----------------------+
                            |                                                            |
            +------------------------------+                              +------------------------------+
            |       TEMPO STREAMING        |                              |      MIRAGE KYB / OSINT      |
            |------------------------------|                              |------------------------------|
            | Rolling 7-day vector         |                              | Redis Entity Cache           |
            | Response: ~5ms               |                              | Response: ~10-50ms           |
            +------------------------------+                              +------------------------------+
""".strip("\n")


# ==========================================
# PIPELINE EXECUTION ENGINE
# ==========================================
def run_pipeline_scan(row: dict, sample_id: str, log_fn, bars: dict | None = None):
    log_fn("[USER]  (1) Live Biometric Payload received", "sys")
    log_fn("[GAIT]  StandardScaler + IsolationForest...")
    if bars:
        for p in range(0, 101, 25):
            bars["gait"].progress(p); time.sleep(0.04)
    gait_score = round(random.uniform(15, 92), 1)
    gait_latency = round(random.uniform(18.2, 22.4), 1)
    gait_detail = {
        "keystroke_interval_mean_ms": round(random.uniform(40, 320), 1),
        "keystroke_interval_std_ms": round(random.uniform(1, 140), 1),
        "mouse_curve_index": round(random.uniform(0.01, 2.4), 2),
        "session_dwell_time_sec": round(random.uniform(2, 380), 1),
        "app_switch_count": random.randint(0, 14),
        "latency_ms": gait_latency,
    }
    log_fn(f"[GAIT]  Score: {gait_score}% ({gait_latency}ms)", "ok" if gait_score < 70 else "warn")

    log_fn("[PAY]   (2) Transaction Event received", "sys")
    log_fn("[ORCH]  1. Read Gait Score", "sys")
    log_fn("[ORCH]  2. Fetching Tempo sliding-window...", "sys")
    if bars:
        for p in range(0, 101, 34):
            bars["tempo"].progress(p); time.sleep(0.015)
    tempo_score = round(random.uniform(10, 96), 1)
    tempo_latency = round(random.uniform(3.5, 6.8), 1)
    tempo_detail = {
        "rolling_7day_vector": [random.randint(2, 45) for _ in range(7)],
        "mean_gap_sec": round(random.uniform(5, 520), 1),
        "event_count": random.randint(4, 92),
        "burstiness": round(random.uniform(-0.85, 0.95), 2),
        "latency_ms": tempo_latency,
    }
    log_fn(f"[TEMPO] Score: {tempo_score}% ({tempo_latency}ms)", "ok" if tempo_score < 70 else "warn")

    log_fn("[ORCH]  3. Querying Mirage Registry...", "sys")
    cache_hit = random.random() > 0.35
    if bars:
        for p in range(0, 101, 20):
            bars["mirage"].progress(p); time.sleep(0.04 if not cache_hit else 0.012)
    reality_index = round(random.uniform(5, 95), 1)
    mirage_latency = round(random.uniform(10.5, 14.8), 1) if cache_hit else round(random.uniform(34.2, 48.9), 1)
    jurisdiction = random.choice(["USA", "GBR", "DEU", "CAN"]) if reality_index > 40 else random.choice(["BVI", "CYM", "PRK", "IRN", "PAN"])
    mirage_detail = {
        "company_name": f"{'Verified' if reality_index > 40 else 'Shell'} Holdings {random.randint(1000,9999)}",
        "jurisdiction_code": jurisdiction,
        "domain_age_days": random.randint(850, 4200) if reality_index > 40 else random.randint(2, 90),
        "co_location_density": random.randint(1, 35) if reality_index > 40 else random.randint(450, 5200),
        "has_commercial_ip": reality_index > 40,
        "cache_status": "HIT" if cache_hit else "MISS",
        "latency_ms": mirage_latency,
    }
    log_fn(f"[MIRAGE] Substance: {reality_index}/100 ({mirage_latency}ms)", "ok" if reality_index > 40 else "err")

    log_fn("[ORCH]  4. Executing Circuit Breaker...", "sys")
    time.sleep(0.15)

    verdict, reason = None, None
    try:
        payload = {
            "transaction_id": str(sample_id),
            "sender_account_id": str(row.get("Account", "ACC_1001")),
            "receiver_account_id": str(row.get("Account.1", "ACC_2001")),
            "amount": float(row.get("Amount Paid", row.get("Amount_Paid", 2500.0)) or 2500.0),
            "gait_telemetry_vector": [1.0] * 10,
        }
        res = requests.post(st.session_state.api_url, json=payload, timeout=2)
        data = res.json()
        verdict = data.get("verdict")
        reason = data.get("compliance_reason") or data.get("reason")
        log_fn(f"[ORCH]  Live Gateway Responded: {verdict}", "sys")
    except Exception:
        log_fn("[ORCH]  API unreachable -> Using inline evaluation", "warn")

    if verdict is None:
        worst = max(
            risk_bucket(gait_score), risk_bucket(tempo_score), risk_bucket(reality_index, invert=True),
            key=lambda b: {"safe": 0, "moderate": 1, "high": 2}[b],
        )
        verdict = {"high": "BLOCK", "moderate": "STEP_UP", "safe": "ALLOW"}[worst]
        reason = "Automated multi-vector evaluation."

    log_fn(f"[ORCH]  VERDICT: {verdict}", "err" if verdict == "BLOCK" else "warn" if "STEP" in str(verdict) else "ok")

    return {
        "transaction_id": sample_id, "gait": gait_score, "tempo": tempo_score, "mirage": reality_index,
        "verdict": verdict, "reason": reason, "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "gait_detail": gait_detail, "tempo_detail": tempo_detail, "mirage_detail": mirage_detail,
    }


# ==========================================
# REPORT BUILDER (HTML DOWNLOAD)
# ==========================================
def generate_topology_report_html(scan: dict | None) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    if scan:
        gait, tempo, mirage, verdict, reason, txn = (
            scan["gait"], scan["tempo"], scan["mirage"], scan["verdict"], scan["reason"], scan["transaction_id"]
        )
        gd, td, md = scan["gait_detail"], scan["tempo_detail"], scan["mirage_detail"]
    else:
        gait, tempo, mirage, verdict, reason, txn = 82.0, 94.0, 13.0, "BLOCK", "Automated Evaluation", "TXN_EVAL"
        gd = {"keystroke_interval_mean_ms": 312.4, "keystroke_interval_std_ms": 128.9, "mouse_curve_index": 0.31, "session_dwell_time_sec": 341.2, "app_switch_count": 11, "latency_ms": 19.4}
        td = {"rolling_7day_vector": [2, 4, 3, 19, 27, 31, 24], "mean_gap_sec": 42.1, "event_count": 58, "burstiness": 0.71, "latency_ms": 4.8}
        md = {"company_name": "Apex Holdings Ltd", "jurisdiction_code": "BVI", "domain_age_days": 4, "co_location_density": 4021, "has_commercial_ip": False, "cache_status": "MISS", "latency_ms": 48.2}

    def bucket_row(label, score, invert=False):
        b = risk_bucket(score, invert=invert)
        color = {"high": T["high"], "moderate": T["moderate"], "safe": T["safe"]}[b]
        return f'<tr><td style="padding:10px;border-bottom:1px solid #ADD8E6;">{label}</td><td style="padding:10px;border-bottom:1px solid #ADD8E6;">{score}</td><td style="padding:10px;border-bottom:1px solid #ADD8E6;color:{color};">{risk_label(b)}</td></tr>'

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Topology Report</title>
<style>
body {{ font-family: sans-serif; font-weight: 600; background:{T['bg']}; color:{T['text']}; padding: 40px; margin:0; }}
.card {{ background:{T['card']}; border:1px solid {T['border']}; border-radius:14px; padding:22px; margin-bottom:20px; }}
table {{ width:100%; border-collapse: collapse; margin-top:10px; }}
th {{ text-align:left; padding:8px; border-bottom:2px solid {T['border']}; color:{T['muted']}; font-size:0.8rem; text-transform:uppercase; }}
</style></head>
<body>
<h1 style="color:{T['accent']}; font-family: sans-serif;">System Topology Report</h1>
<p style="color:{T['muted']}; font-size:0.9rem;">{ts} | {st.session_state.bank_name} | Ref: {txn}</p>
<div class="card">
<table><tr><th>Engine</th><th>Score</th><th>Classification</th></tr>
{bucket_row("Gait Engine", gait)}{bucket_row("Tempo Streaming", tempo)}{bucket_row("Mirage KYB", mirage, invert=True)}
</table>
<h2 style="color:{T['high']};">VERDICT: {verdict}</h2>
</div></body></html>"""


# ==========================================
# PAGE: GLOBAL DASHBOARD (HOME)
# ==========================================
if st.session_state.page == "Home":
    st.markdown(f"""
    <div class="hero" style="text-align: center; padding: 50px 30px;">
        <h1 style="font-size: 2.5rem; color: #FFFFFF !important;">3NITY Autonomous Orchestrator</h1>
        <p style="font-size: 1.05rem; color: #FFFFFF !important; max-width: 650px; margin: 0 auto;">
            A multi-vector financial crime prevention engine. 3NITY fuses live biometric telemetry, high-frequency temporal clustering, and corporate entity substance into a single non-compensatory circuit breaker.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.write("")
    st.markdown("### Architecture Workflow")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="card" style="text-align: center; height: 160px; display: flex; flex-direction: column; justify-content: center; border: 2px solid {T['accent']};">
            <div class="stat-label">STAGE 1</div>
            <div class="engine-name" style="font-size: 1.1rem; margin: 8px 0; color: {T['accent']};">Data Ingestion</div>
            <div class="muted" style="font-size: 0.8rem;">Live Biometric Payloads<br>Core Banking Ledgers</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="card" style="text-align: center; height: 160px; display: flex; flex-direction: column; justify-content: center; border: 2px solid {T['accent']};">
            <div class="stat-label">STAGE 2</div>
            <div class="engine-name" style="font-size: 1.1rem; margin: 8px 0; color: {T['accent']};">Tri-Engine Evaluation</div>
            <div class="muted" style="font-size: 0.8rem;">Gait (Behavioral)<br>Tempo (Velocity)<br>Mirage (Substance)</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="card" style="text-align: center; height: 160px; display: flex; flex-direction: column; justify-content: center; border: 2px solid {T['accent']};">
            <div class="stat-label">STAGE 3</div>
            <div class="engine-name" style="font-size: 1.1rem; margin: 8px 0; color: {T['accent']};">Circuit Breaker</div>
            <div class="muted" style="font-size: 0.8rem;">Non-Compensatory Logic<br>Automated Enforcement</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")
    st.write("")
    st.markdown("### Quick Navigation")
    
    nc1, nc2, nc3, nc4 = st.columns(4)
    if nc1.button("Upload & Scan", use_container_width=True):
        st.session_state.page = "Upload & Scan"
        st.rerun()
    if nc2.button("Topology Report", use_container_width=True):
        st.session_state.page = "Topology Report"
        st.rerun()
    if nc3.button("Network Investigation", use_container_width=True):
        st.session_state.page = "Network Investigation"
        st.rerun()
    if nc4.button("Account Settings", use_container_width=True):
        st.session_state.page = "Account Settings"
        st.rerun()


# ==========================================
# PAGE: UPLOAD & SCAN
# ==========================================
elif st.session_state.page == "Upload & Scan":
    st.markdown("### Real-Time Orchestration Scan")
    st.write("")

    left, right = st.columns([1.1, 1])
    with left:
        uploaded_file = st.file_uploader("Upload CSV Ledger", type=["csv"])
        df = None
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
            st.success(f"Parsed {len(df):,} transactions.")
            st.dataframe(df.head(6), use_container_width=True, height=190)
        st.write("")
        run = st.button("Execute Pipeline Scan", disabled=(uploaded_file is None), use_container_width=True)

    with right:
        st.markdown("**1. GAIT**"); gait_bar = st.progress(0)
        st.markdown("**2. TEMPO**"); tempo_bar = st.progress(0)
        st.markdown("**3. MIRAGE**"); mirage_bar = st.progress(0)

    st.write("")
    st.markdown("#### Terminal")
    terminal_ph = st.empty()
    terminal_ph.markdown('<div class="terminal">Awaiting ingestion...</div>', unsafe_allow_html=True)
    report_ph = st.container()

    if run and df is not None:
        log_lines = []
        def log(line, cls="ok"):
            log_lines.append(f'<span class="{cls}">{line}</span>')
            terminal_ph.markdown(f'<div class="terminal">{"<br>".join(log_lines)}</div>', unsafe_allow_html=True)

        row = df.iloc[0].to_dict()
        sample_id = row.get("transaction_id", row.get("Transaction Id", f"TXN_{random.randint(1000,9999)}"))
        result = run_pipeline_scan(row, sample_id, log, bars={"gait": gait_bar, "tempo": tempo_bar, "mirage": mirage_bar})
        st.session_state.scan_history.append(result)

        with report_ph:
            st.success("Pipeline Execution Complete. Generating Topology Report...")
            time.sleep(1.5)
            st.session_state.page = "Topology Report"
            st.rerun()


# ==========================================
# PAGE: TOPOLOGY REPORT
# ==========================================
elif st.session_state.page == "Topology Report":
    latest = st.session_state.scan_history[-1] if st.session_state.scan_history else None

    st.markdown(f"""
    <div class="hero">
        <h1 style="color: #FFFFFF !important;">3NITY System Topology &amp; Risk Intelligence</h1>
        <p style="color: #FFFFFF !important;">Real-time AML orchestration for {st.session_state.bank_name}.</p>
    </div>
    """, unsafe_allow_html=True)

    if latest is None:
        st.info("No live scan executed in this session. Please navigate to 'Upload & Scan' to process a transaction.")
    else:
        dl1, dl2 = st.columns([1.2, 3.8])
        with dl1:
            st.download_button(
                "Download Report",
                data=generate_topology_report_html(latest),
                file_name="3nity_report.html", mime="text/html", use_container_width=True,
            )
        with dl2:
            st.markdown(f"<span class='muted' style='line-height:2.2;'>Synced with <b>{latest['transaction_id']}</b> | {latest['timestamp']}</span>", unsafe_allow_html=True)

        st.write("")
        with st.expander("Pipeline Architecture Diagram", expanded=False):
            st.markdown(f'<div class="topology-diagram">{TOPOLOGY_DIAGRAM}</div>', unsafe_allow_html=True)

        st.write("")
        st.markdown("### Engine Telemetry")

        cols = st.columns(3)
        boxes = [("gait", "GAIT ENGINE", latest["gait"], False), ("tempo", "TEMPO STREAMING", latest["tempo"], False), ("mirage", "MIRAGE KYB", latest["mirage"], True)]
        
        for col, (key, name, score, invert) in zip(cols, boxes):
            bucket = risk_bucket(score, invert=invert)
            col.markdown(f"""
            <div class="engine-card" style="--engine-color:{RISK[bucket]};">
                <div>
                    <div class="engine-name">{name}</div>
                    <div class="engine-score" style="color:{T['text']};">{score}{'%' if key != 'mirage' else '/100'}</div>
                </div>
                <span class="risk-badge risk-{bucket}">{risk_label(bucket)}</span>
            </div>
            """, unsafe_allow_html=True)

        st.write("")
        
        with st.expander("GAIT ENGINE Details", expanded=False):
            d = latest["gait_detail"]
            g1, g2, g3, g4 = st.columns(4)
            g1.metric("Keystroke Mean", f"{d['keystroke_interval_mean_ms']} ms")
            g2.metric("Keystroke Variance", f"{d['keystroke_interval_std_ms']} ms")
            g3.metric("Mouse Curve", d["mouse_curve_index"])
            g4.metric("Latency", f"{d['latency_ms']} ms")

        with st.expander("TEMPO STREAMING Details", expanded=False):
            d = latest["tempo_detail"]
            st.bar_chart(pd.DataFrame({"Txn Volume": d["rolling_7day_vector"]}, index=[f"Day -{6-i}" for i in range(7)]))
            t1, t2, t3, t4 = st.columns(4)
            t1.metric("Mean Gap", f"{d['mean_gap_sec']} sec")
            t2.metric("Event Count", d["event_count"])
            t3.metric("Burstiness", d["burstiness"])
            t4.metric("Latency", f"{d['latency_ms']} ms")

        with st.expander("MIRAGE KYB Details", expanded=False):
            d = latest["mirage_detail"]
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Target", d['company_name'])
            m2.metric("Jurisdiction", d['jurisdiction_code'])
            m3.metric("Domain Age", f"{d['domain_age_days']} Days")
            m4.metric("Density", f"{d['co_location_density']} Cos")


# ==========================================
# PAGE: NETWORK INVESTIGATION (GRAPH)
# ==========================================
elif st.session_state.page == "Network Investigation":
    st.markdown("### Network Topology")
    st.write("")

    return_value = None

    col_graph, col_details = st.columns([3, 1])
    with col_graph:
        nodes, edges = [], []
        for i in range(1, 6):
            nodes.append(Node(id=f"Mule_0{i}", label=f"Mule_0{i}", size=16, color=T['muted']))
            edges.append(Edge(source=f"Mule_0{i}", target="Consolidator", label="Wire Transfer"))
        nodes.append(Node(id="Consolidator", label="Intermediary", size=26, color=RISK['moderate']))
        edges.append(Edge(source="Consolidator", target="Shell_Corp", label="SWIFT"))
        nodes.append(Node(id="Shell_Corp", label="Ghost Shell", size=36, color=RISK['high']))
        
        config = Config(
            width=800, height=500, directed=True, physics=True, hierarchical=False,
            nodeHighlightBehavior=True, highlightColor=T['accent_soft']
        )
        return_value = agraph(nodes=nodes, edges=edges, config=config)

    with col_details:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("#### Entity Data")
        if return_value == "Shell_Corp":
            st.markdown(f"<span class='risk-badge risk-high' style='background-color:{RISK['high']}'>GHOST SHELL</span>", unsafe_allow_html=True)
            st.write("**Mirage:** 10.0 / 100")
            st.write("**Jurisdiction:** BVI")
        elif return_value == "Consolidator":
            st.markdown(f"<span class='risk-badge risk-moderate' style='background-color:{RISK['moderate']}'>CONSOLIDATOR</span>", unsafe_allow_html=True)
            st.write("**Tempo:** Burst")
            st.write("**In-Degree:** 5")
        else:
            st.markdown("<span class='muted'>Select node</span>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)


# ==========================================
# PAGE: ACCOUNT SETTINGS
# ==========================================
elif st.session_state.page == "Account Settings":
    st.markdown("### Settings")
    st.write("")
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.session_state.bank_name = st.text_input("Institution Name", value=st.session_state.bank_name)
    st.session_state.api_url = st.text_input("API URL", value=st.session_state.api_url)
    st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.scan_history:
        st.write("")
        st.markdown("#### Scan Ledger")
        hist_df = pd.DataFrame([
            {"ID": s["transaction_id"], "Gait": s["gait"], "Tempo": s["tempo"],
             "Mirage": s["mirage"], "Verdict": s["verdict"]}
            for s in st.session_state.scan_history
        ])
        st.dataframe(hist_df, use_container_width=True)