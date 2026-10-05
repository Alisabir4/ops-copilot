import os
from html import escape
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

API=os.getenv("API_BASE_URL",os.getenv("API_URL","http://localhost:8000")).rstrip("/")
px.defaults.template="plotly_white"
px.defaults.color_discrete_sequence=["#2563EB","#0F766E","#7C3AED","#D97706","#0891B2"]
st.set_page_config(page_title="Ops Copilot",page_icon="◈",layout="wide",initial_sidebar_state="expanded")
st.markdown("""<style>
:root{color-scheme:light;--ops-ink:#172B4D;--ops-muted:#5B6B82;--ops-blue:#2563EB;--ops-border:#E2E8F0;--ops-canvas:#F4F7FB}
.stApp,[data-testid="stAppViewContainer"]{background:var(--ops-canvas);color:var(--ops-ink);font-family:Inter,"Segoe UI",Arial,sans-serif}
[data-testid="stHeader"]{background:rgba(244,247,251,.92)}
.block-container{padding:1.15rem 2rem 3rem;max-width:1500px}
h1,h2,h3,h4,h5,p,label,[data-testid="stMarkdownContainer"]{color:var(--ops-ink)}
h1{font-size:1.75rem;letter-spacing:-.035em}h2{font-size:1.22rem;letter-spacing:-.02em}h3{font-size:1.02rem}
.page-header{display:flex;align-items:center;justify-content:space-between;gap:1rem;padding:.35rem 0 1rem;margin-bottom:1.15rem;border-bottom:1px solid #E6EBF2}
.page-heading h1{font-size:1.72rem;line-height:1.2;margin:0;color:#13243A;font-weight:700}
.page-heading p{font-size:.88rem;color:#63728A;margin:.38rem 0 0}
.header-actions{display:flex;align-items:center;gap:.65rem;flex:none}
.mode-pill{padding:.35rem .58rem;border:1px solid #D7E4F5;border-radius:6px;background:#F1F6FD;color:#315D91;font-size:.68rem;font-weight:750;letter-spacing:.08em}
.header-avatar{width:34px;height:34px;display:grid;place-items:center;border-radius:50%;background:#E5EEFC;border:1px solid #D0DFF6;color:#244F89;font-size:.72rem;font-weight:750}
.metric{height:100%;box-sizing:border-box;background:#fff;border:1px solid var(--ops-border);border-radius:9px;padding:1rem 1.05rem;box-shadow:0 1px 3px #19324b06}
.metric h2{color:var(--ops-ink);font-size:1.48rem;line-height:1.2;white-space:nowrap;margin:.52rem 0 .25rem;font-weight:700}.small{color:var(--ops-muted);font-size:.73rem;font-weight:650;letter-spacing:.035em}
.metric-note{color:#8190A3;font-size:.73rem;line-height:1.35}
.section-head{display:flex;align-items:baseline;justify-content:space-between;gap:.8rem;margin:.4rem 0 .65rem}
.section-head h2{margin:0;font-size:1.06rem;color:#1A2D46;font-weight:700}
.section-head span{color:#738198;font-size:.76rem}
.surface{height:100%;box-sizing:border-box;background:#fff;border:1px solid var(--ops-border);border-radius:9px;padding:1rem 1.05rem;box-shadow:0 1px 3px #19324b06}
.insight-surface{height:100%;box-sizing:border-box;background:#F8FAFD;border:1px solid #DFE8F3;border-left:3px solid #3B82F6;border-radius:8px;padding:1.05rem}
.eyebrow{color:#6D7D92;font-size:.68rem;font-weight:750;letter-spacing:.1em;text-transform:uppercase}
.status-chip{display:inline-flex;align-items:center;padding:.23rem .5rem;border-radius:5px;background:#EFF4FA;color:#475569;font-size:.7rem;font-weight:650}
.status-ok{background:#EAF6EF;color:#276749}.status-warn{background:#FFF5E6;color:#8A5A13}.status-danger{background:#FDECEC;color:#A33A3A}.status-blue{background:#EAF1FC;color:#28568F}
.data-row{padding:.72rem 0;border-bottom:1px solid #EDF1F5;font-size:.82rem;color:#33445B}
.data-row:last-child{border-bottom:0}.muted{color:#748198;font-size:.78rem}
.chat-surface{background:#fff;border:1px solid var(--ops-border);border-radius:10px;padding:1rem 1.1rem;min-height:250px}
.prompt-card{height:100%;padding:.72rem .78rem;border:1px solid #E0E7F0;border-radius:8px;background:#fff;color:#33445B;font-size:.78rem;line-height:1.4}
.timeline-item{position:relative;margin-left:.35rem;padding:.15rem 0 1rem 1.15rem;border-left:1px solid #DCE5EF}
.timeline-item:before{content:"";position:absolute;left:-5px;top:.3rem;width:8px;height:8px;border:2px solid #fff;border-radius:50%;background:#4B83D0;box-shadow:0 0 0 1px #AFC7E7}
.timeline-title{color:#24354B;font-size:.84rem;font-weight:650}.timeline-meta{color:#7B899B;font-size:.73rem;margin-top:.25rem}
.st-key-login_shell{max-width:470px;margin:8vh auto 0;padding:2rem!important;background:#fff;border:1px solid var(--ops-border);border-radius:10px;box-shadow:0 8px 28px #19324b0b}
.login-brand{display:flex;align-items:center;gap:.8rem;margin-bottom:1.4rem}
.login-mark{width:42px;height:42px;display:grid;place-items:center;background:#172B49;border-radius:10px;color:#DBEAFE;font-size:20px}
[data-testid="stSidebar"]{background:#0F172A;border-right:1px solid #1E293B;color:#F8FAFC;width:260px!important;min-width:260px!important}
[data-testid="stSidebar"] [data-testid="stSidebarContent"]{padding:.8rem .72rem .7rem}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p{color:#CBD5E1}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"]{color:#94A3B8}
[data-testid="stSidebar"] .brand-lockup{display:flex;align-items:center;gap:.72rem;margin:.15rem .25rem .85rem}
[data-testid="stSidebar"] .brand-mark{width:36px;height:36px;display:grid;place-items:center;background:#172B49;border:1px solid #27456F;border-radius:10px;flex:none}
[data-testid="stSidebar"] .brand-copy{line-height:1.2}
[data-testid="stSidebar"] .brand-name{font-size:16px;font-weight:700;letter-spacing:-.025em;color:#F8FAFC}
[data-testid="stSidebar"] .brand-subtitle{font-size:11px;color:#94A3B8;margin-top:3px}
[data-testid="stSidebar"] .workspace-switcher{padding:.58rem .65rem;margin:.1rem 0 .75rem;border:1px solid #263449;border-radius:8px;background:#141F32;transition:background .15s,border-color .15s}
[data-testid="stSidebar"] .workspace-switcher:hover{background:#19273D;border-color:#3A4D68}
[data-testid="stSidebar"] .workspace-overline{font-size:9px;font-weight:700;letter-spacing:.12em;color:#8493A8}
[data-testid="stSidebar"] .workspace-name{display:flex;align-items:center;gap:.5rem;margin-top:.35rem;color:#F1F5F9;font-size:12px;font-weight:600}
[data-testid="stSidebar"] .nav-section{margin:.62rem .55rem .22rem;color:#74839A;font-size:10px;font-weight:700;letter-spacing:.12em}
[data-testid="stSidebar"] [class*="st-key-nav_"]{margin:0 0 .16rem}
[data-testid="stSidebar"] [class*="st-key-nav_"] button{width:100%;justify-content:flex-start;min-height:34px;padding:.32rem .58rem;border:1px solid transparent;border-radius:7px;background:transparent;color:#B8C4D4;font-size:13px;font-weight:500;text-align:left;transition:background .14s,color .14s,border-color .14s}
[data-testid="stSidebar"] [class*="st-key-nav_"] button:hover{background:#19263A;border-color:#26374E;color:#F8FAFC}
[data-testid="stSidebar"] [class*="st-key-nav_"] button [data-testid="stIconMaterial"]{color:#8595AA;font-size:18px}
[data-testid="stSidebar"] [class*="st-key-nav_"] button:hover [data-testid="stIconMaterial"]{color:#BFDBFE}
[data-testid="stSidebar"] [class*="st-key-nav_"] button:focus-visible{outline:2px solid #60A5FA;outline-offset:1px}
[data-testid="stSidebar"] .profile-area{position:fixed;left:0;bottom:2.8rem;width:260px;box-sizing:border-box;margin:0;padding:.55rem .72rem .05rem;border-top:1px solid #263449;background:#0F172A;z-index:1000}
[data-testid="stSidebar"] .profile-row{display:flex;align-items:center;gap:.65rem;padding:.35rem .28rem .55rem}
[data-testid="stSidebar"] .profile-avatar{width:32px;height:32px;display:grid;place-items:center;border-radius:50%;background:#233B5E;color:#DBEAFE;font-size:11px;font-weight:700}
[data-testid="stSidebar"] .profile-name{color:#F1F5F9;font-size:12px;font-weight:600;line-height:1.3}
[data-testid="stSidebar"] .profile-role{color:#94A3B8;font-size:11px;margin-top:2px}
[data-testid="stSidebar"] .st-key-sign_out{position:fixed;left:0;bottom:0;width:260px;box-sizing:border-box;padding:.2rem .72rem .45rem;background:#0F172A;z-index:1000}
[data-testid="stSidebar"] .st-key-sign_out button{width:100%;min-height:32px;justify-content:flex-start;background:transparent;border-color:transparent;color:#9EACC0;font-size:12px}
[data-testid="stSidebar"] .st-key-sign_out button:hover{background:#19263A;border-color:#26374E;color:#F1F5F9}
[data-testid="stButton"] button,[data-testid="stFormSubmitButton"] button{border-radius:9px;border:1px solid #CBD5E1;background:#fff;color:#1E293B;font-weight:650;min-height:2.55rem;transition:all .15s}
[data-testid="stButton"] button:hover,[data-testid="stFormSubmitButton"] button:hover{border-color:#7AA7F7;color:#1749A3;background:#F7FAFF}
[data-testid="stButton"] button[kind="primary"],[data-testid="stFormSubmitButton"] button[kind="primary"]{background:var(--ops-blue);border-color:var(--ops-blue);color:#fff}
[data-testid="stButton"] button[kind="primary"]:hover,[data-testid="stFormSubmitButton"] button[kind="primary"]:hover{background:#1D4ED8;border-color:#1D4ED8;color:#fff}
button:focus-visible,input:focus-visible,textarea:focus-visible{outline:3px solid #93B4FF!important;outline-offset:2px!important}
input,textarea{color:#172B4D!important;background:#fff!important;border-color:#CBD5E1!important}
[data-baseweb="select"]>div{background:#fff;color:#172B4D;border-color:#CBD5E1}
[data-testid="stDataFrame"],[data-testid="stTable"],[data-testid="stPlotlyChart"],[data-testid="stForm"]{background:#fff;border:1px solid var(--ops-border);border-radius:9px;box-shadow:0 1px 3px #19324b06;overflow:hidden}
[data-testid="stDataFrame"]{padding:.15rem}[data-testid="stPlotlyChart"]{padding:.35rem}
[data-testid="stAlert"]{border-radius:10px;border:1px solid var(--ops-border)}[data-testid="stAlert"] p{color:#26364B!important}
[data-testid="stExpander"]{background:#fff;border:1px solid var(--ops-border);border-radius:10px}
[data-testid="stCaptionContainer"]{color:var(--ops-muted)}
.source{background:#EFF5FF;border:1px solid #D8E6FF;border-radius:8px;padding:.55rem .8rem;margin:.35rem 0;color:#234A7A;font-size:.88rem}
@media(max-width:900px){.block-container{padding:.85rem 1rem 2rem}.page-header{align-items:flex-start}.page-heading h1{font-size:1.48rem}.metric{padding:.78rem}.metric h2{font-size:1.18rem}.header-actions{gap:.4rem}}
@media(max-width:600px){.header-actions .mode-pill{display:none}.page-header{gap:.4rem}.page-heading p{font-size:.8rem}.page-heading h1{font-size:1.35rem}.header-avatar{width:30px;height:30px}}
</style>""",unsafe_allow_html=True)

if "token" not in st.session_state: st.session_state.token=""
if "messages" not in st.session_state: st.session_state.messages=[]
if "conversation_id" not in st.session_state: st.session_state.conversation_id=None

def api(path,method="GET",**kwargs):
    headers=kwargs.pop("headers",{});headers.update({"Authorization":f"Bearer {st.session_state.token}"})
    try:
        r=requests.request(method,API+path,headers=headers,timeout=30,**kwargs)
        if r.status_code>=400: st.error(r.json().get("detail","The request could not be completed."));return None
        return r.json() if r.content else {}
    except requests.RequestException: st.error("Could not reach the backend. Start FastAPI and check API_URL.");return None

def style_chart(fig):
    fig.update_layout(
        template="plotly_white",
        font={"family":"Inter, Segoe UI, Arial, sans-serif","color":"#334155","size":12},
        title_font={"color":"#172B4D","size":16},
        paper_bgcolor="rgba(255,255,255,0)",plot_bgcolor="#FFFFFF",
        legend={"font":{"color":"#334155"},"bgcolor":"rgba(255,255,255,.85)"},
        hoverlabel={"bgcolor":"#153451","font":{"color":"#FFFFFF"}},
        margin={"l":18,"r":14,"t":52,"b":20},
    )
    fig.update_xaxes(title_font={"color":"#334155"},tickfont={"color":"#475569"},gridcolor="#EDF1F6",linecolor="#CBD5E1")
    fig.update_yaxes(title_font={"color":"#334155"},tickfont={"color":"#475569"},gridcolor="#EDF1F6",linecolor="#CBD5E1",zerolinecolor="#CBD5E1")
    return fig

if not st.session_state.token:
    with st.container(key="login_shell",border=True):
        st.markdown('<div class="login-brand"><div class="login-mark">◈</div><div><strong>Ops Copilot</strong><div class="muted">AI Business Operations</div></div></div>',unsafe_allow_html=True)
        st.title("Welcome back")
        st.caption("Sign in to your operations workspace.")
        with st.form("login"):
            email=st.text_input("Email",value="admin@demo.local");password=st.text_input("Password",value="",type="password")
            if st.form_submit_button("Continue",type="primary",width="stretch"):
                try:
                    res=requests.post(API+"/auth/login",json={"email":email,"password":password},timeout=10)
                    if res.ok:st.session_state.token=res.json()["access_token"];st.session_state.user=res.json()["user"];st.rerun()
                    else:st.error("Sign-in failed. Check credentials and backend status.")
                except requests.RequestException:st.error("Backend is unavailable. Start the API first.")
    st.stop()

user=api("/auth/me") or st.session_state.get("user",{})
NAV_GROUPS=[
    ("WORKSPACE",[("Overview","dashboard"),("AI Copilot","auto_awesome"),("Documents","description")]),
    ("BUSINESS",[("Inventory","inventory_2"),("Sales","shopping_cart"),("Customers","group"),("Analytics","bar_chart")]),
    ("AUTOMATION",[("Approvals","task_alt"),("Automations","bolt"),("Activity","monitoring")]),
    ("SYSTEM",[("Settings","settings")]),
]
if "current_page" not in st.session_state: st.session_state.current_page="Overview"
with st.sidebar:
    st.markdown('''<div class="brand-lockup"><div class="brand-mark"><svg width="21" height="21" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 3.5 19.5 7.8v8.4L12 20.5l-7.5-4.3V7.8L12 3.5Z" stroke="#93C5FD" stroke-width="1.6"/><path d="M8.2 12h2.1l1.2-2.5 1.4 5 1.1-2.5h1.8" stroke="#F8FAFC" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg></div><div class="brand-copy"><div class="brand-name">Ops Copilot</div><div class="brand-subtitle">AI Business Operations</div></div></div>''',unsafe_allow_html=True)
    workspace_kind="DEMO WORKSPACE" if os.getenv("DEMO_MODE","true").lower()=="true" else "LIVE WORKSPACE"
    st.markdown(f'''<div class="workspace-switcher"><div class="workspace-overline">{workspace_kind}</div><div class="workspace-name"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M3.5 20V8.5L12 4l8.5 4.5V20h-17Z" stroke="#94A3B8" stroke-width="1.6" stroke-linejoin="round"/><path d="M8 20v-5h8v5M8 9.5h.01M12 9.5h.01M16 9.5h.01" stroke="#94A3B8" stroke-width="1.6" stroke-linecap="round"/></svg>Demo Business <span style="margin-left:auto;color:#718096">⌄</span></div></div>''',unsafe_allow_html=True)
    for section,items in NAV_GROUPS:
        st.markdown(f'<div class="nav-section">{section}</div>',unsafe_allow_html=True)
        for label,icon in items:
            key=label.lower().replace(" ","_")
            with st.container(key=f"nav_{key}",border=False):
                if st.button(label,icon=f":material/{icon}:",key=f"nav_button_{key}",width="stretch"):
                    st.session_state.current_page=label
                    st.rerun()
            if st.session_state.current_page==label:
                st.markdown(f'<style>[data-testid="stSidebar"] .st-key-nav_{key} button{{background:#1A2C47;border-color:#28466D;color:#F8FAFC;font-weight:650;box-shadow:inset 2px 0 #3B82F6}}[data-testid="stSidebar"] .st-key-nav_{key} button [data-testid="stIconMaterial"]{{color:#60A5FA}}</style>',unsafe_allow_html=True)
    initials="".join(part[0].upper() for part in user.get("name","Team Member").split()[:2])
    st.markdown(f'''<div class="profile-area"><div class="profile-row"><div class="profile-avatar">{initials}</div><div><div class="profile-name">{user.get('name','Team member')}</div><div class="profile-role">{user.get('role','employee').title()}</div></div></div></div>''',unsafe_allow_html=True)
    if st.button("Sign out",icon=":material/logout:",key="sign_out",width="stretch"):
        st.session_state.token="";st.session_state.messages=[];st.rerun()
page=st.session_state.current_page

def hero(title,sub):
    """Render the consistent page header and compact app-level context."""
    initials="".join(part[0].upper() for part in user.get("name","Team Member").split()[:2])
    mode="DEMO WORKSPACE" if os.getenv("DEMO_MODE","true").lower()=="true" else "LIVE WORKSPACE"
    st.markdown(f'<header class="page-header"><div class="page-heading"><h1>{escape(title)}</h1><p>{escape(sub)}</p></div><div class="header-actions"><span class="mode-pill">{mode}</span><span class="header-avatar" title="{escape(user.get("name","Team member"))}">{escape(initials)}</span></div></header>',unsafe_allow_html=True)

def section_header(title,detail=""):
    """Render a reusable section title and optional context label."""
    st.markdown(f'<div class="section-head"><h2>{escape(title)}</h2><span>{escape(detail)}</span></div>',unsafe_allow_html=True)

def metric_row(items,columns=None):
    """Render consistent, compact metric cards from backend-derived values."""
    cols=st.columns(columns or len(items))
    for col,item in zip(cols,items):
        label,value,note=item
        col.markdown(f'<div class="metric"><div class="small">{escape(str(label))}</div><h2>{escape(str(value))}</h2><div class="metric-note">{escape(str(note))}</div></div>',unsafe_allow_html=True)

def trend_frame(rows):
    """Validate and normalize the public revenue trend response schema."""
    frame=pd.DataFrame(rows or [])
    if not {"sold_at","revenue"}.issubset(frame.columns):
        return pd.DataFrame(columns=["sold_at","revenue"])
    frame["sold_at"]=pd.to_datetime(frame["sold_at"],errors="coerce",utc=True)
    frame["revenue"]=pd.to_numeric(frame["revenue"],errors="coerce")
    return frame.dropna(subset=["sold_at","revenue"]).sort_values("sold_at")

def money(x):return f"${float(x or 0):,.0f}"

if page=="Overview":
    hero("Good to see you, "+user.get("name","team").split()[0],"Here is the latest view of your business.")
    d=api("/dashboard/summary") or {}
    metric_row([("Revenue · 30 days",money(d.get("revenue")),"Recorded sales revenue"),("Transactions",d.get("orders",0),"Last 30 days"),("Customers",d.get("customers",0),"In the customer base"),("Average transaction",money(d.get("average_order_value")),"Last 30 days"),("Low stock",d.get("low_stock",0),"At or below threshold")])
    st.write("")
    trend=trend_frame(api("/sales/trend?days=90") or [])
    low=api("/inventory/low-stock") or []
    tops=d.get("top_products",[])
    chart_col,insight_col=st.columns([1.75,1],gap="large")
    with chart_col:
        section_header("Revenue pulse","Daily · last 90 days")
        if not trend.empty:
            st.plotly_chart(style_chart(px.area(trend,x="sold_at",y="revenue",labels={"sold_at":"Date","revenue":"Revenue"},title=None)),width="stretch")
        else:
            st.info("Revenue trend will appear when sales are recorded.")
    with insight_col:
        section_header("Business signals","From recorded data")
        top_product=tops[0] if tops else None
        signal_rows=[f'<div class="data-row"><strong>{len(low)} products</strong> are at or below their reorder threshold.</div>']
        if top_product:
            signal_rows.append(f'<div class="data-row"><strong>{escape(top_product["name"])}</strong> leads recorded product revenue at {money(top_product["revenue"])}.</div>')
        signal_rows.append(f'<div class="data-row">Inventory value is <strong>{money(d.get("inventory_value"))}</strong> at cost.</div>')
        st.markdown('<div class="insight-surface"><div class="eyebrow">OPERATIONS SNAPSHOT</div>'+"".join(signal_rows)+'</div>',unsafe_allow_html=True)
        if st.button("Explore analytics",key="overview_analytics"):
            st.session_state.current_page="Analytics";st.rerun()
    tops_col,alerts_col=st.columns([1.15,1],gap="large")
    with tops_col:
        section_header("Top products","By recorded revenue")
        if tops:
            st.dataframe(pd.DataFrame(tops).rename(columns={"name":"Product","units":"Units","revenue":"Revenue"}),hide_index=True,width="stretch",height=260)
        else:st.info("Product performance will appear when sales are recorded.")
    with alerts_col:
        section_header("Inventory alerts",f"{len(low)} items need attention")
        if low:
            st.dataframe(pd.DataFrame(low).rename(columns={"name":"Product","stock":"On hand","reorder_level":"Reorder at"}),hide_index=True,width="stretch",height=260)
        else:st.success("No items need attention.")
    section_header("Recent transactions","Last 7 days")
    recent=api("/sales?days=7") or []
    if recent:
        recent_frame=pd.DataFrame(recent).head(6)
        recent_frame["sold_at"]=pd.to_datetime(recent_frame["sold_at"],errors="coerce",utc=True)
        st.dataframe(recent_frame.rename(columns={"sold_at":"Date","customer":"Customer","product":"Product","quantity":"Qty","revenue":"Revenue"})[["Date","Customer","Product","Qty","Revenue"]],hide_index=True,width="stretch",height=270)
    else:st.info("No recent transactions found.")

elif page=="AI Copilot":
    hero("AI Copilot","Ask about business performance, company knowledge, or a proposed next step.")
    saved=api("/conversations") or []
    selector,button=st.columns([3,1])
    choice=selector.selectbox("Recent conversations",[None]+saved,format_func=lambda x:"Start a new conversation" if x is None else f"{x['title']} · #{x['id']}",label_visibility="collapsed")
    if button.button("Open",disabled=choice is None):
        loaded=api(f"/conversations/{choice['id']}")
        if loaded:
            st.session_state.conversation_id=loaded["id"]
            st.session_state.messages=[{"role":m["role"],"content":m["content"],"sources":[]} for m in loaded["messages"]]
            st.rerun()
    if selector.button("＋ New conversation"):st.session_state.messages=[];st.session_state.conversation_id=None;st.rerun()
    suggested_prompt=None
    if not st.session_state.messages:
        st.markdown('<div class="chat-surface"><div class="eyebrow">YOUR OPERATIONS WORKSPACE</div><h3>What would you like to understand?</h3><p class="muted">Ask a business question, search company knowledge, or prepare an action for review.</p></div>',unsafe_allow_html=True)
        prompt_cols=st.columns(4)
        suggestions=["Why did revenue change this month?","Which products are low stock?","Summarize our sales performance.","What does our return policy say?"]
        for col,suggestion in zip(prompt_cols,suggestions):
            with col:
                st.markdown(f'<div class="prompt-card">{escape(suggestion)}</div>',unsafe_allow_html=True)
                if st.button("Ask this",key="suggest_"+str(suggestions.index(suggestion)),width="stretch"):
                    suggested_prompt=suggestion
    with st.container(key="copilot_history",border=True):
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                for source in msg.get("sources",[]):
                    st.markdown(f'<div class="source">{escape(source["filename"])}'+(f' · Page {source["page"]}' if source.get("page") else "")+'</div>',unsafe_allow_html=True)
    prompt=st.chat_input("Ask Ops Copilot about your business…") or suggested_prompt
    if prompt:
        st.session_state.messages.append({"role":"user","content":prompt})
        with st.chat_message("user"):st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Checking business data and knowledge…"):res=api("/copilot/chat","POST",json={"message":prompt,"conversation_id":st.session_state.conversation_id})
            if res:
                st.session_state.conversation_id=res.get("conversation_id")
                st.markdown(res.get("answer",""));
                if res.get("tools") or res.get("sources") or res.get("data"):
                    with st.expander("Sources & actions",expanded=bool(res.get("sources"))):
                        if res.get("tools"):st.caption("Tools used · "+", ".join(t["name"] for t in res["tools"]))
                        for source in res.get("sources",[]):st.markdown(f'<div class="source">{escape(source["filename"])}'+(f' · Page {source["page"]}' if source.get("page") else "")+'</div>',unsafe_allow_html=True)
                        if res.get("data") and res.get("kind")!="answer":
                            data=res["data"]
                            if isinstance(data,list) and data:st.dataframe(pd.DataFrame(data),hide_index=True,width="stretch")
                            else:st.json(data)
                st.session_state.messages.append({"role":"assistant","content":res.get("answer",""),"sources":res.get("sources",[])})
    st.caption("Sensitive actions are prepared for human review before execution.")

elif page=="Documents":
    hero("Documents","Manage the knowledge base used for policy and operations answers.")
    docs=api("/documents") or []
    chunks=sum(int(doc.get("chunk_count") or 0) for doc in docs)
    indexed=sum(doc.get("status")=="processed" for doc in docs)
    last_updated=pd.to_datetime(docs[0].get("created_at"),errors="coerce",utc=True).strftime("%b %d, %Y") if docs and pd.notna(pd.to_datetime(docs[0].get("created_at"),errors="coerce",utc=True)) else "—"
    metric_row([("Documents",len(docs),"In this workspace"),("Chunks",chunks,"Searchable passages"),("Indexed",indexed,"Ready for retrieval"),("Last updated",last_updated,"Most recent upload")])
    st.write("")
    left,right=st.columns([1.5,1],gap="large")
    with left:
        section_header("Knowledge base","Uploaded business documents")
    with right:
        if user.get("role") in ("admin","manager"):
            file=st.file_uploader("Upload a document",type=["pdf","txt","md","docx"],label_visibility="collapsed")
            if file and st.button("Upload and index",type="primary",icon=":material/upload_file:"):
                result=api("/documents/upload","POST",files={"file":(file.name,file.getvalue(),file.type)})
                if result:st.success(f"Indexed {result['chunk_count']} chunks from {result['filename']}.");st.rerun()
    if docs:
        docs_frame=pd.DataFrame(docs).rename(columns={"filename":"Document","content_type":"Type","status":"Status","chunk_count":"Chunks","created_at":"Uploaded"})
        docs_frame["Status"]=docs_frame["Status"].map({"processed":"Indexed","processing":"Processing","failed":"Failed"}).fillna(docs_frame["Status"].str.title())
        docs_frame["Uploaded"]=pd.to_datetime(docs_frame["Uploaded"],errors="coerce",utc=True).dt.strftime("%b %d, %Y")
        st.dataframe(docs_frame[["Document","Type","Chunks","Status","Uploaded"]],hide_index=True,width="stretch",height=min(420,100+len(docs)*38))
        if user.get("role") in ("admin","manager"):
            with st.expander("Document maintenance"):
                for doc in docs:
                    row,action=st.columns([5,1])
                    row.caption(f"{doc['filename']} · {doc['chunk_count']} chunks")
                    if action.button("Delete",key=f"delete_document_{doc['id']}",icon=":material/delete_outline:"):
                        if api(f"/documents/{doc['id']}","DELETE"):st.success("Document removed from the knowledge base.");st.rerun()
    else:
        st.markdown('<div class="surface"><div class="eyebrow">KNOWLEDGE BASE</div><h3>No documents indexed yet</h3><p class="muted">Upload a policy, handbook, or operating guide to enable answers with document citations.</p></div>',unsafe_allow_html=True)
    with st.expander("Built-in demo knowledge"):st.caption("Company Policies.md includes return/refund and replenishment policy examples.")

elif page=="Inventory":
    hero("Inventory","Stock health and reorder thresholds across your catalog.")
    items=api("/inventory") or [];df=pd.DataFrame(items)
    if not df.empty:
        out_of_stock=int((df.stock==0).sum())
        low_count=int(df.status.isin(["Low","Critical","Out of Stock"]).sum())
        metric_row([("Products",len(df),"In the catalog"),("Low stock",low_count,"At or below threshold"),("Out of stock",out_of_stock,"Unavailable now"),("Inventory value",money((df.stock*df.cost).sum()),"Estimated at cost")])
        st.write("")
        c1,c2=st.columns(2);search=c1.text_input("Search products");cat=c2.selectbox("Category",["All"]+sorted(df.category.unique().tolist()))
        view=df[df.name.str.contains(search,case=False)] if search else df
        if cat!="All":view=view[view.category==cat]
        section_header("Product stock",f"{len(view)} products")
        st.dataframe(view.rename(columns={"sku":"SKU","name":"Product","category":"Category","price":"Unit price","stock":"On hand","reorder_level":"Threshold","status":"Status"})[["Product","SKU","Category","Unit price","On hand","Threshold","Status"]],hide_index=True,width="stretch",height=520)
        st.caption("Reorder proposals can be prepared in AI Copilot and require an administrator or manager decision.")
    else:
        metric_row([("Products",0,"In the catalog"),("Low stock",0,"At or below threshold"),("Out of stock",0,"Unavailable now"),("Inventory value",money(0),"Estimated at cost")])
        st.info("No inventory records are available.")

elif page=="Sales":
    hero("Sales","Recorded sales activity and transaction-level performance.")
    days=st.select_slider("Period",options=[7,30,60,90,180,365],value=90,format_func=lambda x:f"{x} days")
    summary=api(f"/sales/summary?days={days}") or {}
    metric_row([("Revenue",money(summary.get("revenue")),f"Recorded · {days} days"),("Transactions",summary.get("orders",0),"In selected period"),("Average transaction",money(summary.get("average_order_value")),"Revenue per transaction"),("Units sold",summary.get("units",0),"In selected period")])
    st.write("")
    section_header("Revenue trend",f"Daily · last {days} days")
    trend=trend_frame(api(f"/sales/trend?days={days}") or [])
    if not trend.empty:
        st.plotly_chart(style_chart(px.area(trend,x="sold_at",y="revenue",labels={"sold_at":"Date","revenue":"Revenue"})),width="stretch")
    else:st.info("Revenue trend will appear when sales are recorded in this period.")
    section_header("Recent sales","Latest transactions in the selected window")
    records=api(f"/sales?days={days}") or []
    if records:
        frame=pd.DataFrame(records);frame["sold_at"]=pd.to_datetime(frame["sold_at"],errors="coerce",utc=True)
        st.dataframe(frame.sort_values("sold_at",ascending=False).rename(columns={"sold_at":"Date","customer":"Customer","product":"Product","quantity":"Qty","unit_price":"Unit price","revenue":"Revenue"})[["Date","Customer","Product","Qty","Unit price","Revenue"]],hide_index=True,width="stretch",height=500)
    else:st.info("No sales have been recorded in this period.")

elif page=="Customers":
    hero("Customers","Understand customer segments and purchase activity.")
    query=st.text_input("Search customers",placeholder="Search by name")
    customers=api("/customers?search="+requests.utils.quote(query)) or []
    customer_frame=pd.DataFrame(customers)
    if not customer_frame.empty:
        repeat=int((customer_frame.orders>1).sum());single=int((customer_frame.orders==1).sum());inactive=int((customer_frame.orders==0).sum())
        metric_row([("Customers",len(customer_frame),"In the customer base"),("Repeat",repeat,"More than one transaction"),("Single transaction",single,"One recorded transaction"),("No transactions",inactive,"No recorded purchases")])
        st.write("")
        section_header("Customer directory",f"{len(customer_frame)} customers")
        st.dataframe(customer_frame.rename(columns={"name":"Customer","email":"Email","segment":"Segment","orders":"Transactions"})[["Customer","Email","Segment","Transactions"]],hide_index=True,width="stretch",height=520)
    else:st.info("No matching customers. Try a different name or clear the search.")

elif page=="Analytics":
    hero("Analytics","Explore revenue trends, product mix, and customer activity from recorded data.")
    d=api("/dashboard/summary") or {};tops=d.get("top_products",[]);customers=api("/customers") or []
    metric_row([("Revenue · 30 days",money(d.get("revenue")),"Recorded sales"),("Transactions",d.get("orders",0),"Last 30 days"),("Customers",len(customers),"In the database"),("Inventory attention",d.get("low_stock",0),"At or below threshold")])
    st.write("")
    trend=trend_frame(api("/sales/trend?days=90") or [])
    sales=api("/sales?days=90") or []
    sales_frame=pd.DataFrame(sales)
    if not sales_frame.empty and "sold_at" in sales_frame:
        sales_frame["sold_at"]=pd.to_datetime(sales_frame["sold_at"],errors="coerce",utc=True)
        sales_frame=sales_frame.dropna(subset=["sold_at"])
        sales_frame["day"]=sales_frame.sold_at.dt.floor("D")
        order_trend=sales_frame.groupby("day",as_index=False).agg(transactions=("id","nunique"))
    else:order_trend=pd.DataFrame(columns=["day","transactions"])
    left,right=st.columns(2,gap="large")
    with left:
        section_header("Revenue trends","Daily · last 90 days")
        if not trend.empty:st.plotly_chart(style_chart(px.line(trend,x="sold_at",y="revenue",markers=True,labels={"sold_at":"Date","revenue":"Revenue"})),width="stretch")
        else:st.info("No revenue observations for this period.")
    with right:
        section_header("Transaction volume","Daily · last 90 days")
        if not order_trend.empty:st.plotly_chart(style_chart(px.bar(order_trend,x="day",y="transactions",labels={"day":"Date","transactions":"Transactions"})),width="stretch")
        else:st.info("No transactions for this period.")
    product_col,customer_col=st.columns(2,gap="large")
    with product_col:
        section_header("Top products","By recorded revenue")
        if tops:
            f=pd.DataFrame(tops)
            st.plotly_chart(style_chart(px.bar(f,x="revenue",y="name",orientation="h",labels={"name":"Product","revenue":"Revenue"})),width="stretch")
            st.caption("Product totals reflect available sales history.")
        else:st.info("Product analytics will appear after sales are recorded.")
    with customer_col:
        section_header("Customer activity","Recorded transaction count by segment")
        if customers:
            customer_df=pd.DataFrame(customers)
            segment_counts=customer_df.groupby("segment",as_index=False).agg(customers=("id","count"))
            st.plotly_chart(style_chart(px.bar(segment_counts,x="segment",y="customers",labels={"segment":"Segment","customers":"Customers"})),width="stretch")
        else:st.info("No customer activity is available yet.")
    dlow=d.get("low_stock",0)
    st.markdown(f'<div class="insight-surface"><div class="eyebrow">DATA SIGNAL</div><strong>{dlow} products</strong> are currently at or below their reorder thresholds. Review the inventory workspace before preparing any reorder proposal.</div>',unsafe_allow_html=True)
    if st.button("Prepare weekly business report",type="primary"):
        report=api("/reports/business?days=7")
        if report:st.session_state.report=report["markdown"]
    if st.session_state.get("report"):
        st.markdown(st.session_state.report);st.download_button("Download Markdown report",st.session_state.report,file_name="business-report.md",mime="text/markdown")

elif page=="Approvals":
    hero("Approvals","Review proposed actions before they can reach connected workflows.")
    items=api("/approvals") or []
    pending=sum(item.get("status")=="pending" for item in items)
    metric_row([("Pending review",pending,"Awaiting a decision"),("Approved",sum(item.get("status")=="approved" for item in items),"In approval history"),("Rejected",sum(item.get("status")=="rejected" for item in items),"In approval history")])
    st.write("")
    section_header("Action requests","Approval is required before sensitive work is executed")
    if not items:st.markdown('<div class="surface"><div class="eyebrow">APPROVAL QUEUE</div><h3>Nothing needs your review</h3><p class="muted">AI-prepared actions will appear here with their proposed details.</p></div>',unsafe_allow_html=True)
    for item in items:
        with st.container(key=f"approval_card_{item['id']}",border=True):
            title=escape(item["action_type"].replace("_"," ").title())
            badge="status-warn" if item.get("status")=="pending" else "status-ok" if item.get("status")=="approved" else "status-danger"
            requested=pd.to_datetime(item.get("created_at"),errors="coerce",utc=True)
            when=requested.strftime("%b %d, %Y · %H:%M UTC") if pd.notna(requested) else "Date unavailable"
            st.markdown(f'<div class="eyebrow">ACTION REQUEST</div><h3 style="margin:.3rem 0">{title}</h3><span class="status-chip {badge}">{escape(item.get("status","unknown").title())}</span> <span class="status-chip status-blue">Requires approval</span><p class="muted">Requested by {escape(item.get("requested_by","Team member"))} · {when}</p>',unsafe_allow_html=True)
            payload=item.get("payload",{})
            if isinstance(payload,list) and payload:
                st.dataframe(pd.DataFrame(payload).rename(columns={"product":"Product","stock":"On hand","reorder_level":"Reorder at","suggested_quantity":"Suggested qty"}),hide_index=True,width="stretch")
            elif payload:st.json(payload)
            if item.get("decision_note"):st.caption("Decision note · "+item["decision_note"])
            note=st.text_input("Decision note",key=f"note{item['id']}",placeholder="Optional context for the audit trail")
            if item["status"]=="pending" and user.get("role") in ("admin","manager"):
                x,y=st.columns(2)
                if x.button("Approve",key=f"a{item['id']}",type="primary"):api(f"/approvals/{item['id']}/approve","POST",json={"note":note});st.rerun()
                if y.button("Reject",key=f"r{item['id']}"):api(f"/approvals/{item['id']}/reject","POST",json={"note":note});st.rerun()

elif page=="Automations":
    hero("Automations","Connect approved business actions to your configured workflow provider.")
    demo=os.getenv("DEMO_MODE","true").lower()=="true"
    webhook=bool(os.getenv("N8N_WEBHOOK_URL"))
    status="Demo simulation" if demo else "Connected" if webhook else "Not connected"
    status_class="status-blue" if demo else "status-ok" if webhook else "status-warn"
    st.markdown(f'<div class="surface"><div class="eyebrow">WORKFLOW PROVIDER</div><h3 style="margin:.35rem 0">n8n integration</h3><span class="status-chip {status_class}">{status}</span><p class="muted">Approved actions are delivered through the configured webhook. Sensitive actions remain approval-gated.</p></div>',unsafe_allow_html=True)
    st.write("")
    section_header("Available workflows","Availability depends on configured n8n workflows")
    workflow_cols=st.columns(3)
    workflows=[("Low-stock alert","Route approved inventory attention to a notification workflow."),("Weekly business report","Send a generated business summary through n8n."),("Approved reorder","Deliver an approved reorder proposal to the purchasing workflow.")]
    for col,(name,description) in zip(workflow_cols,workflows):
        with col:
            st.markdown(f'<div class="surface"><div class="eyebrow">WORKFLOW</div><h3>{escape(name)}</h3><p class="muted">{escape(description)}</p><span class="status-chip {status_class}">{status}</span></div>',unsafe_allow_html=True)
    st.write("")
    logs=api("/automations/logs") or []
    section_header("Execution history",f"{len(logs)} recorded events")
    if logs:st.dataframe(pd.DataFrame(logs).rename(columns={"event":"Event","status":"Delivery status","summary":"Result","created_at":"Time"})[["Event","Delivery status","Result","Time"]],hide_index=True,width="stretch",height=360)
    else:st.info("No automation activity has been recorded yet.")

elif page=="Activity":
    hero("Activity","A traceable timeline of sign-ins, AI retrieval, and business actions.")
    logs=api("/audit-logs")
    if logs:
        frame=pd.DataFrame(logs)
        section_header("Recent activity",f"{len(frame)} events")
        for _,entry in frame.head(50).iterrows():
            timestamp=pd.to_datetime(entry.get("timestamp"),errors="coerce",utc=True)
            when=timestamp.strftime("%b %d · %H:%M UTC") if pd.notna(timestamp) else "Time unavailable"
            title=escape(str(entry.get("event","Activity")).replace("_"," ").title())
            detail=" · ".join(str(entry.get(key,"")) for key in ("user","resource","details") if pd.notna(entry.get(key)) and str(entry.get(key)).strip())
            st.markdown(f'<div class="timeline-item"><div class="timeline-title">{title}</div><div class="timeline-meta">{when} · {escape(detail)}</div></div>',unsafe_allow_html=True)
    else:st.info("Activity is available to manager and administrator roles.")

elif page=="Settings":
    hero("Settings","Workspace preferences and connected service status.")
    health=api("/health") or {}
    metric_row([("API","Connected" if health.get("status")=="ok" else "Unavailable","FastAPI service"),("Workspace","Demo" if health.get("demo_mode",True) else "Live","Current operating mode"),("AI provider","Groq configured" if os.getenv("GROQ_API_KEY") and os.getenv("GROQ_MODEL") else "Local tools","Provider credentials stay private"),("Automation","Webhook configured" if os.getenv("N8N_WEBHOOK_URL") else "Not configured","n8n integration")])
    st.write("")
    ai_ready=bool(os.getenv("GROQ_API_KEY") and os.getenv("GROQ_MODEL"))
    profile_tab,security_tab,ai_tab,data_tab,automation_tab,app_tab=st.tabs(["Profile","Security","AI configuration","Database","Automation","Application"])
    with profile_tab:
        section_header("Profile","Signed-in account")
        st.markdown(f'<div class="surface"><strong>{escape(user.get("name","Team member"))}</strong><p class="muted">{escape(user.get("email",""))} · {escape(user.get("role","employee").title())}</p></div>',unsafe_allow_html=True)
    with security_tab:
        section_header("Security","Authentication and access")
        st.markdown('<div class="surface"><span class="status-chip status-ok">JWT session active</span><p class="muted">Access is protected by your assigned server-side role.</p></div>',unsafe_allow_html=True)
    with ai_tab:
        section_header("AI provider","Model and credentials are managed by the backend")
        st.markdown(f'<div class="surface"><strong>{"Groq" if ai_ready else "Local business tools"}</strong><p class="muted">{ "Provider configured" if ai_ready else "External model credentials are not configured; local tool routing remains available."}</p><span class="status-chip {"status-ok" if ai_ready else "status-blue"}">{"Connected" if ai_ready else "Local mode"}</span></div>',unsafe_allow_html=True)
    with data_tab:
        section_header("Database","Connection status")
        st.markdown(f'<div class="surface"><strong>{"Configured" if os.getenv("DATABASE_URL") else "Application default"}</strong><p class="muted">Database credentials are read by the backend and are never displayed here.</p></div>',unsafe_allow_html=True)
    with automation_tab:
        section_header("n8n automation","Delivery status")
        st.markdown(f'<div class="surface"><strong>{"Webhook configured" if os.getenv("N8N_WEBHOOK_URL") else "Not configured"}</strong><p class="muted">{ "Demo mode simulates external delivery." if health.get("demo_mode",True) else "Approved actions only are sent to the configured webhook."}</p></div>',unsafe_allow_html=True)
    with app_tab:
        section_header("Application","Workspace status")
        st.markdown('<div class="surface"><strong>Ops Copilot</strong><p class="muted">AI Business Operations Platform · Frontend connected to FastAPI.</p></div>',unsafe_allow_html=True)
