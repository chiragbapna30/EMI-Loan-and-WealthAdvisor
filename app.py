import html
import pandas as pd
import plotly.express as px
import streamlit as st

from agent import EMILoanAgent, generate_amortization_schedule, inr
import chat_store as store

# Page Config
st.set_page_config(
    page_title="EMI, Loan & Wealth Advisor", 
    page_icon="🏦", 
    layout="centered",
    initial_sidebar_state="expanded"
)

# ----------------------------------------------------------------------------
# COMPREHENSIVE DARK MODE CSS (RESTORES SIDEBAR TOGGLE & DARK FOOTER)
# ----------------------------------------------------------------------------
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Outfit:wght@500;600;700;800&display=swap');

:root {
    --bg-gradient: linear-gradient(135deg, #0b0f19 0%, #111827 50%, #0b0f19 100%);
    --card-bg: rgba(30, 41, 59, 0.85);
    --border-glow: rgba(99, 102, 241, 0.35);
    --primary-glow: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%);
    --accent-teal: #14b8a6;
    --accent-gold: #f59e0b;
    --text-main: #f8fafc;
    --text-muted: #cbd5e1;
}

/* Base Setup */
html, body, [class*="css"], .stApp {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    background: var(--bg-gradient) !important;
    color: var(--text-main) !important;
}

#MainMenu, footer { visibility: hidden; }

/* ----------------------------------------------------------------------------
   RESTORE & FORCE TOP-LEFT SIDEBAR TOGGLE ICON VISIBILITY
---------------------------------------------------------------------------- */
header[data-testid="stHeader"] { 
    background: transparent !important; 
    visibility: visible !important;
    display: block !important;
    z-index: 999999 !important;
}

button[data-testid="stSidebarToggle"], 
[data-testid="stHeader"] button,
[data-testid="stSidebarCollapseButton"],
[data-testid="collapsedControl"] {
    display: flex !important;
    visibility: visible !important;
    color: #ffffff !important;
    background: rgba(30, 41, 59, 0.95) !important;
    border: 1px solid rgba(255, 255, 255, 0.25) !important;
    border-radius: 10px !important;
    z-index: 1000000 !important;
}

.block-container {
    max-width: 880px;
    padding-top: 2rem;
    padding-bottom: 6rem;
}

/* Hero Header Card */
.hero-card {
    background: rgba(15, 23, 42, 0.85);
    border: 1px solid var(--border-glow);
    border-radius: 20px;
    padding: 28px 32px;
    margin-bottom: 1.2rem;
    box-shadow: 0 15px 30px rgba(0, 0, 0, 0.5);
    backdrop-filter: blur(12px);
    position: relative;
    overflow: hidden;
}
.hero-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; height: 4px;
    background: var(--primary-glow);
}
.hero-card h1 {
    font-family: 'Outfit', sans-serif !important;
    font-weight: 800;
    font-size: 2.2rem;
    color: #ffffff !important;
    margin: 0 0 8px 0;
}
.hero-card p {
    color: var(--text-muted) !important;
    font-size: 1.05rem;
    margin: 0;
    line-height: 1.5;
}

/* ----------------------------------------------------------------------------
   FORCE BOTTOM FOOTER & CHAT INPUT TO MATCH DARK BACKGROUND
---------------------------------------------------------------------------- */
[data-testid="stBottom"],
[data-testid="stBottom"] > div,
footer[data-testid="stFooter"] {
    background: #0b0f19 !important;
    background-color: #0b0f19 !important;
    border-top: 1px solid rgba(255, 255, 255, 0.08) !important;
}

[data-testid="stChatInput"],
.stChatInputContainer,
div[data-testid="stChatInputContainer"] {
    background-color: rgba(30, 41, 59, 0.95) !important;
    border: 1px solid rgba(99, 102, 241, 0.5) !important;
    border-radius: 16px !important;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5) !important;
}

[data-testid="stChatInput"] textarea,
[data-testid="stChatInput"] input,
.stChatInputContainer textarea {
    color: #ffffff !important;
    background-color: transparent !important;
    caret-color: #ffffff !important;
    font-size: 1rem !important;
    font-weight: 500 !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: #94a3b8 !important;
    font-weight: 400 !important;
}

[data-testid="stChatInput"] button {
    background-color: #6366f1 !important;
    color: #ffffff !important;
    border-radius: 10px !important;
}

/* ----------------------------------------------------------------------------
   UNIVERSAL TEXT VISIBILITY FIX
---------------------------------------------------------------------------- */
label, 
p, 
span, 
h1, h2, h3, h4, h5, h6,
.stSelectbox label, 
.stSelectbox p,
[data-testid="stWidgetLabel"] p,
[data-testid="stMarkdownContainer"] p,
.stExpander details summary p {
    color: #f8fafc !important;
    opacity: 1 !important;
}

.stExpander details summary span,
.stExpander details summary div {
    color: #f8fafc !important;
    font-weight: 700 !important;
}

div[data-baseweb="select"] > div {
    background-color: rgba(30, 41, 59, 0.95) !important;
    color: #ffffff !important;
    border: 1px solid rgba(255, 255, 255, 0.25) !important;
    border-radius: 10px !important;
}

div[data-baseweb="select"] span {
    color: #ffffff !important;
    font-weight: 600 !important;
}

div[data-baseweb="popover"] div, 
div[data-baseweb="menu"] div {
    background-color: #1e293b !important;
    color: #ffffff !important;
}

/* ----------------------------------------------------------------------------
   QUICK PROMPT SUGGESTION BUTTONS
---------------------------------------------------------------------------- */
div[data-testid="stHorizontalBlock"] .stButton > button {
    background: rgba(30, 41, 59, 0.8) !important;
    border: 1px solid rgba(255, 255, 255, 0.15) !important;
    border-radius: 12px !important;
    padding: 12px 14px !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
}

div[data-testid="stHorizontalBlock"] .stButton > button p {
    color: transparent !important;
    font-weight: 600 !important;
    font-size: 0.92rem !important;
    transition: color 0.3s ease !important;
    text-shadow: none !important;
}

div[data-testid="stHorizontalBlock"] .stButton > button:hover {
    background: rgba(99, 102, 241, 0.25) !important;
    border-color: #818cf8 !important;
    transform: translateY(-3px) scale(1.02);
    box-shadow: 0 8px 20px rgba(99, 102, 241, 0.4) !important;
}
div[data-testid="stHorizontalBlock"] .stButton > button:hover p {
    color: #ffffff !important;
}

/* ----------------------------------------------------------------------------
   CHAT MESSAGES & CHAT TEXT VISIBILITY
---------------------------------------------------------------------------- */
[data-testid="stChatMessage"] {
    background: var(--card-bg) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 18px !important;
    padding: 18px 22px !important;
    margin-bottom: 16px !important;
    box-shadow: 0 10px 25px rgba(0,0,0,0.3) !important;
}

[data-testid="stChatMessage"] *, 
[data-testid="stChatMessage"] p, 
[data-testid="stChatMessage"] li, 
[data-testid="stChatMessage"] span,
[data-testid="stChatMessage"] div {
    color: #f8fafc !important;
    font-size: 1rem !important;
    line-height: 1.6 !important;
}

[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]),
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background: rgba(99, 102, 241, 0.2) !important;
    border: 1px solid rgba(129, 140, 248, 0.4) !important;
}

/* Tables inside chat */
[data-testid="stChatMessage"] table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    border-radius: 12px;
    overflow: hidden;
    margin: 1rem 0;
    border: 1px solid rgba(255,255,255,0.15);
}
[data-testid="stChatMessage"] thead th {
    background: #1e1b4b !important;
    color: #ffffff !important;
    padding: 12px 14px;
    font-weight: 700;
}
[data-testid="stChatMessage"] tbody td {
    padding: 12px 14px;
    background: rgba(15, 23, 42, 0.8) !important;
    border-top: 1px solid rgba(255,255,255,0.08);
}

/* Sidebar Styling & History Buttons */
section[data-testid="stSidebar"] {
    background: rgba(11, 15, 25, 0.98) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
}
section[data-testid="stSidebar"] * { color: var(--text-main) !important; }

section[data-testid="stSidebar"] .stButton > button {
    background: var(--primary-glow) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    padding: 0.65rem 1rem !important;
    box-shadow: 0 4px 15px rgba(99, 102, 241, 0.35) !important;
}

section[data-testid="stSidebar"] [class*="st-key-hist"] .stButton > button {
    background: rgba(255, 255, 255, 0.05) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 10px !important;
    box-shadow: none !important;
}
section[data-testid="stSidebar"] [class*="st-key-hist"] .stButton > button p {
    color: #f8fafc !important;
}
section[data-testid="stSidebar"] [class*="st-key-histactive"] .stButton > button {
    background: rgba(99, 102, 241, 0.3) !important;
    border-color: #818cf8 !important;
}

section[data-testid="stSidebar"] [class*="st-key-histdel"] .stButton > button {
    background: rgba(239, 68, 68, 0.2) !important;
    border: 1px solid rgba(239, 68, 68, 0.4) !important;
    border-radius: 10px !important;
}

.mem-card {
    background: rgba(30, 41, 59, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 10px 14px;
    margin-bottom: 8px;
}
.mem-card .label { font-size: 0.75rem; color: var(--text-muted) !important; text-transform: uppercase; letter-spacing: 0.05em; }
.mem-card .value { font-size: 1.05rem; font-weight: 700; color: #ffffff !important; margin-top: 2px; }
.mem-card .value.accent { color: var(--accent-gold) !important; }

/* File Chips */
.file-chip {
    display: inline-block;
    background: rgba(20, 184, 166, 0.2);
    border: 1px solid rgba(20, 184, 166, 0.4);
    border-radius: 20px;
    padding: 6px 14px;
    margin: 4px 6px 6px 0;
    font-size: 0.85rem;
    color: #5eead4 !important;
}

.side-brand { font-family: 'Outfit', sans-serif; font-size: 1.3rem; font-weight: 800; color: #ffffff !important; margin: 0 0 14px 2px; }
.side-group { font-size: 0.75rem; color: var(--text-muted) !important; margin: 16px 0 6px 4px; font-weight: 700; text-transform: uppercase; }
.side-empty { font-size: 0.85rem; color: var(--text-muted) !important; padding: 8px 4px; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# HERO HEADER
# ----------------------------------------------------------------------------
st.markdown(
    """
    <div class="hero-card">
        <h1>🏦 EMI, Loan & Wealth Advisor</h1>
        <p>Your AI financial companion. Share your loan goals, analyze affordability, 
        compare repayment options, or explore legal strategies to multiply wealth in India.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

ALLOWED_FILES = ["png", "jpg", "jpeg", "webp", "pdf", "txt", "csv"]
FILE_NOTE = ("📎 I've saved your attachment. If using Gemini mode, "
             "I will analyze its financial content. In offline mode, please type key loan parameters.")

# ----------------------------------------------------------------------------
# CHAT SESSION HELPERS
# ----------------------------------------------------------------------------
def activate(chat_id, saved=None):
    agent = EMILoanAgent()
    if saved:
        agent.memory.update(saved["memory"])
    st.session_state.agent = agent
    st.session_state.chat_id = chat_id
    st.session_state.confirm_delete = None
    st.query_params["chat"] = chat_id

def cb_new_chat():
    activate(store.new_id())

def cb_open_chat(chat_id):
    saved = store.load_chat(chat_id)
    if saved:
        activate(chat_id, saved)

def cb_ask_delete(chat_id):
    st.session_state.confirm_delete = chat_id

def cb_cancel_delete():
    st.session_state.confirm_delete = None

def cb_delete_chat(chat_id):
    store.delete_chat(chat_id)
    if chat_id == st.session_state.chat_id:
        activate(store.new_id())
    st.session_state.confirm_delete = None

# First load setup
if "agent" not in st.session_state:
    store.migrate_legacy()
    wanted = st.query_params.get("chat")
    saved = store.load_chat(wanted)
    if not saved:
        chats = store.list_chats()
        saved = store.load_chat(chats[0]["id"]) if chats else None
    if saved:
        activate(saved["id"], saved)
    else:
        activate(store.new_id())

agent = st.session_state.agent
chat_id = st.session_state.chat_id
hist = agent.memory["conversation_history"]

# ----------------------------------------------------------------------------
# QUICK PROMPT CHIPS
# ----------------------------------------------------------------------------
st.markdown("<span style='color: #cbd5e1; font-weight: 600; font-size: 0.9rem;'>✨ Hover over boxes to reveal prompt details:</span>", unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)
chip_prompt = None

if c1.button("📌 20 L @ 8.5% 5 yrs", use_container_width=True):
    chip_prompt = "I need a loan of 20 lakh at 8.5% interest rate for 5 years. My salary is 80000."
if c2.button("📊 Compare 3 vs 5 Yrs", use_container_width=True):
    chip_prompt = "Compare 10 lakh loan at 9% for 3 years and 5 years"
if c3.button("📄 Home Loan Docs", use_container_width=True):
    chip_prompt = "What documents are required for a home loan application?"
if c4.button("🚀 Multiply Money", use_container_width=True):
    chip_prompt = "How can I legally multiply money in India?"

# ----------------------------------------------------------------------------
# CHAT INPUT & FILE ATTACHMENTS
# ----------------------------------------------------------------------------
prompt = st.chat_input(
    "Ask about loan options, share income, or upload files...",
    accept_file="multiple",
    file_type=ALLOWED_FILES,
) or chip_prompt

if prompt:
    if isinstance(prompt, str):
        text, files = prompt.strip(), []
    else:
        text, files = (prompt["text"] or "").strip(), list(prompt["files"] or [])

    saved_files = [store.save_attachment(chat_id, f.name, f.getvalue()) for f in files]

    if text:
        agent.run_step(text)
        if saved_files:
            hist[-2]["attachments"] = saved_files
            hist[-1]["content"] += "\n\n---\n" + FILE_NOTE
            hist[-1].setdefault("trace", []).append(f"[Files] Saved {len(saved_files)} attachment(s).")
    elif saved_files:
        hist.append({"role": "user", "content": "", "attachments": saved_files})
        hist.append({"role": "assistant", "content": FILE_NOTE,
                     "trace": [f"[Files] Saved {len(saved_files)} attachment(s)."]})

    store.save_chat(chat_id, agent.memory)
    st.rerun()

# ----------------------------------------------------------------------------
# SIDEBAR NAVIGATION, BANK COMPARISON, GOLD/SILVER RATES & MEMORY CARDS
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown('<div class="side-brand">🏦 Loan Advisor</div>', unsafe_allow_html=True)
    st.button("＋  New Chat", key="newchat", on_click=cb_new_chat, use_container_width=True)

    # --- INDIAN BANK HOME LOAN RATE COMPARISON ---
    with st.expander("🏛️ Major Indian Banks Rates (2026)", expanded=False):
        st.markdown("Select a bank to query its starting home loan rate:")
        bank_rates = {
            "SBI": "7.25% p.a.",
            "HDFC Bank": "7.75% p.a.",
            "ICICI Bank": "8.50% p.a.",
            "Axis Bank": "8.75% p.a.",
            "Bank of Baroda": "8.40% p.a.",
            "Kotak Mahindra": "8.70% p.a."
        }
        selected_bank = st.selectbox("Compare Indian Lenders:", list(bank_rates.keys()))
        rate_val = bank_rates[selected_bank]
        st.info(f"**{selected_bank}** Home Loan starting rate: **{rate_val}**")
        
        if st.button(f"Calculate with {selected_bank}", use_container_width=True):
            rate_num = float(rate_val.replace("% p.a.", ""))
            agent.run_step(f"Calculate EMI for 20 lakh loan at {rate_num}% for 5 years with my salary")
            store.save_chat(chat_id, agent.memory)
            st.rerun()

    # --- INDIAN GOLD & SILVER RATES ---
    with st.expander("🪙 Gold & Silver Rates in India (2026)", expanded=False):
        st.markdown(
            """
            <div class="mem-card" style="border-left: 4px solid #f59e0b;">
                <div class="label">24K Gold (per 10g)</div>
                <div class="value accent">₹76,450</div>
            </div>
            <div class="mem-card" style="border-left: 4px solid #e2e8f0;">
                <div class="label">22K Gold (per 10g)</div>
                <div class="value">₹70,080</div>
            </div>
            <div class="mem-card" style="border-left: 4px solid #94a3b8;">
                <div class="label">Silver (per 1 kg)</div>
                <div class="value" style="color: #cbd5e1 !important;">₹89,200</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Ask Gold Loan Eligibility", use_container_width=True):
            agent.run_step("How do gold loans work and what is the maximum loan amount I can get against gold in India?")
            store.save_chat(chat_id, agent.memory)
            st.rerun()

    query = st.text_input("Search chats", key="q_search", placeholder="Search chat history...", label_visibility="collapsed")
    chats = store.search_chats(query)

    if not chats:
        st.markdown('<div class="side-empty">No chats found.</div>', unsafe_allow_html=True)

    last_group = None
    for c in chats:
        group = store.group_label(c["updated"])
        if group != last_group:
            st.markdown(f'<div class="side-group">{group}</div>', unsafe_allow_html=True)
            last_group = group

        label = c["title"]
        if st.session_state.confirm_delete == c["id"]:
            st.caption(f"Delete “{label}”?")
            b1, b2 = st.columns(2)
            b1.button("Delete", key=f"histyes_{c['id']}", on_click=cb_delete_chat, args=(c["id"],), use_container_width=True)
            b2.button("Keep", key=f"histno_{c['id']}", on_click=cb_cancel_delete, use_container_width=True)
            continue

        is_active = c["id"] == chat_id
        row_open, row_del = st.columns([6, 1])
        row_open.button(label, key=f"{'histactive' if is_active else 'hist'}_{c['id']}", on_click=cb_open_chat, args=(c["id"],), use_container_width=True)
        row_del.button("🗑", key=f"histdel_{c['id']}", on_click=cb_ask_delete, args=(c["id"],), help="Delete chat", use_container_width=True)

    with st.expander("🧠 Agent Memory State"):
        inc = agent.memory["monthly_income"]
        income_txt = "₹{:,.0f}".format(inc) if inc else "Not provided"
        yes_no = lambda v: "Yes" if v else "No"
        score = agent.memory.get("credit_score")
        st.markdown(
            f"""
            <div class="mem-card"><div class="label">Monthly Income</div>
                <div class="value accent">{income_txt}</div></div>
            <div class="mem-card"><div class="label">No Regular Income</div>
                <div class="value">{yes_no(agent.memory['no_income'])}</div></div>
            <div class="mem-card"><div class="label">No Credit History</div>
                <div class="value">{yes_no(agent.memory['no_credit'])}</div></div>
            <div class="mem-card"><div class="label">Credit Score</div>
                <div class="value">{int(score) if score else 'Not provided'}</div></div>
            <div class="mem-card"><div class="label">Calculated Options</div>
                <div class="value">{len(agent.memory['computed_options'])}</div></div>
            """,
            unsafe_allow_html=True,
        )

# ----------------------------------------------------------------------------
# MAIN DISPLAY: MESSAGES & CHARTS
# ----------------------------------------------------------------------------
for msg in hist:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant" and msg.get("trace"):
            with st.expander("Agent Thinking & Tool Calls", expanded=False):
                for log in msg["trace"]:
                    st.write(log)
        
        for att in msg.get("attachments") or []:
            path = store.attachment_path(att)
            if att.get("is_image") and path:
                st.image(str(path), width=280, caption=att["name"])
            else:
                st.markdown(
                    f'<span class="file-chip">📎 {html.escape(att["name"])} · {store.human_size(att.get("size", 0))}</span>',
                    unsafe_allow_html=True)

        if msg.get("content"):
            st.markdown(msg["content"])

# Render Amortization Plotly Chart and Export Button when options exist
if agent.memory.get("computed_options"):
    opts = agent.memory["computed_options"]
    st.write("---")
    
    with st.expander("📈 Interactive Amortization Schedule Chart", expanded=True):
        selected_opt = st.selectbox(
            "Select Loan Option to Analyze:",
            options=range(len(opts)),
            format_func=lambda i: f"Option {i+1}: {inr(opts[i]['amount'])} @ {opts[i]['rate_annual']}% for {opts[i]['months']} Months"
        )
        opt_data = opts[selected_opt]
        schedule = generate_amortization_schedule(opt_data["amount"], opt_data["rate_annual"], opt_data["months"])
        df_schedule = pd.DataFrame(schedule)
        
        fig = px.bar(
            df_schedule, 
            x="Month", 
            y=["Principal Paid", "Interest Paid"], 
            title=f"Repayment Breakdown: Option {selected_opt + 1}",
            labels={"value": "Amount (₹)", "variable": "Payment Type"},
            color_discrete_map={"Principal Paid": "#14b8a6", "Interest Paid": "#f59e0b"},
            template="plotly_dark"
        )
        
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Plus Jakarta Sans, sans-serif", color="#f8fafc", size=14),
            title=dict(font=dict(color="#ffffff", size=18)),
            legend=dict(font=dict(color="#ffffff")),
            xaxis=dict(title_font=dict(color="#ffffff"), tickfont=dict(color="#f8fafc")),
            yaxis=dict(title_font=dict(color="#ffffff"), tickfont=dict(color="#f8fafc"))
        )
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("📥 Export Comparison Summary", expanded=False):
        df_opts = pd.DataFrame(opts)
        csv_bytes = df_opts.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Comparison Summary (CSV)",
            data=csv_bytes,
            file_name="loan_comparison_summary.csv",
            mime="text/csv"
        )
