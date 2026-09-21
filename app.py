import html

import streamlit as st
from agent import EMILoanAgent
import chat_store as store

st.set_page_config(page_title="EMI & Loan Advisor Agent", page_icon="🏦", layout="centered")

# ----------------------------------------------------------------------------
# STYLING  (CSS injected into Streamlit)
# Palette:  ink #0F2A43 | teal #0E7C7B | mist #F1F6F5 | marigold #E9B44C | slate #1B2B3A
# Fonts:    Fraunces (headings) + Plus Jakarta Sans (body)
# ----------------------------------------------------------------------------
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

:root {
    --ink: #0F2A43;
    --ink-soft: #1C3F5E;
    --teal: #0E7C7B;
    --teal-light: #D7EEEC;
    --mist: #F1F6F5;
    --marigold: #E9B44C;
    --slate: #1B2B3A;
    --muted: #5B6B7A;
    --line: #DCE6E4;
    --card: #FFFFFF;
}

/* ---------- Base ---------- */
html, body, [class*="css"], .stApp, .stMarkdown, p, li, label, input, textarea {
    font-family: 'Plus Jakarta Sans', system-ui, -apple-system, 'Segoe UI', sans-serif !important;
    color: var(--slate);
}
.stApp {
    background:
        radial-gradient(900px 400px at 100% -10%, rgba(14,124,123,0.10), transparent 60%),
        radial-gradient(700px 380px at -10% 0%, rgba(233,180,76,0.12), transparent 55%),
        var(--mist);
}
/* hide Streamlit's default chrome */
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }

.block-container {
    max-width: 860px;
    padding-top: 2rem;
    padding-bottom: 6rem;
}

/* ---------- Hero header ---------- */
.hero {
    background: linear-gradient(135deg, var(--ink) 0%, var(--ink-soft) 60%, var(--teal) 130%);
    border-radius: 20px;
    padding: 28px 32px;
    margin-bottom: 1.6rem;
    box-shadow: 0 14px 34px rgba(15, 42, 67, 0.22);
    border-left: 6px solid var(--marigold);
}
.hero h1 {
    font-family: 'Fraunces', Georgia, serif !important;
    font-weight: 700;
    font-size: 2.2rem;
    line-height: 1.15;
    letter-spacing: -0.01em;
    color: #FFFFFF !important;
    margin: 0 0 6px 0;
    padding: 0;
}
.hero p {
    color: #C9DCE8 !important;
    margin: 0;
    font-size: 1rem;
    max-width: 60ch;
}

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"] {
    background: var(--ink);
    border-right: 1px solid rgba(255,255,255,0.06);
}
section[data-testid="stSidebar"] * { color: #E6EEF5 !important; }
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    font-family: 'Fraunces', Georgia, serif !important;
    color: #FFFFFF !important;
}
.mem-card {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 14px;
    padding: 12px 14px;
    margin-bottom: 10px;
}
.mem-card .label { font-size: 0.78rem; color: #9FB6C8 !important; margin-bottom: 2px; }
.mem-card .value { font-size: 1.05rem; font-weight: 600; color: #FFFFFF !important; }
.mem-card .value.accent { color: var(--marigold) !important; }

section[data-testid="stSidebar"] .stButton > button {
    width: 100%;
    background: var(--marigold);
    color: var(--ink) !important;
    border: none;
    border-radius: 12px;
    font-weight: 700;
    padding: 0.6rem 1rem;
    transition: transform .15s ease, box-shadow .15s ease;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 8px 18px rgba(233,180,76,0.35);
}
section[data-testid="stSidebar"] .stButton > button p { color: var(--ink) !important; }
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: #9FB6C8 !important; }

/* ---------- Chat messages ---------- */
[data-testid="stChatMessage"] {
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 16px 20px;
    margin-bottom: 14px;
    box-shadow: 0 6px 18px rgba(15, 42, 67, 0.06);
}
/* user bubbles get a teal tint */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]),
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background: var(--teal-light);
    border-color: #BFE0DD;
}
[data-testid="stChatMessage"] h3 {
    font-family: 'Fraunces', Georgia, serif !important;
    color: var(--ink);
    font-size: 1.25rem;
    margin-top: 0;
}
[data-testid="stChatMessage"] strong { color: var(--ink); }

/* ---------- Tables (loan comparison) ---------- */
[data-testid="stChatMessage"] table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    border: 1px solid var(--line);
    border-radius: 12px;
    overflow: hidden;
    font-size: 0.88rem;
    margin: 0.6rem 0 1rem;
}
[data-testid="stChatMessage"] thead th {
    background: var(--ink);
    color: #FFFFFF !important;
    font-weight: 600;
    text-align: left;
    padding: 10px 12px;
    border: none;
}
[data-testid="stChatMessage"] tbody td {
    padding: 10px 12px;
    border-top: 1px solid var(--line);
    border-left: none; border-right: none;
    background: #FFFFFF;
}
[data-testid="stChatMessage"] tbody tr:nth-child(even) td { background: #F7FBFA; }
[data-testid="stChatMessage"] tbody tr:hover td { background: var(--teal-light); }

/* ---------- Expander (agent trace) ---------- */
[data-testid="stExpander"] {
    border: 1px dashed #B7CFCB;
    border-radius: 12px;
    background: #F7FBFA;
    margin-bottom: 10px;
}
[data-testid="stExpander"] summary { font-weight: 600; color: var(--teal); }

/* ---------- Chat input ---------- */
[data-testid="stChatInput"] {
    border-radius: 16px;
    border: 1.5px solid var(--line);
    background: #FFFFFF;
    box-shadow: 0 10px 28px rgba(15, 42, 67, 0.10);
}
[data-testid="stChatInput"]:focus-within {
    border-color: var(--teal);
    box-shadow: 0 0 0 3px rgba(14,124,123,0.18);
}
[data-testid="stChatInput"] textarea { font-size: 1rem; }

/* ---------- Keyboard focus + small screens ---------- */
button:focus-visible, summary:focus-visible { outline: 3px solid var(--marigold); outline-offset: 2px; }
@media (max-width: 640px) {
    .hero { padding: 20px; }
    .hero h1 { font-size: 1.6rem; }
    [data-testid="stChatMessage"] table { display: block; overflow-x: auto; }
}
/* ---------- Sidebar: brand, search, chat history ---------- */
.side-brand { font-family: 'Fraunces', Georgia, serif; font-size: 1.25rem; font-weight: 700;
              color: #FFFFFF !important; margin: 0 0 12px 2px; }
.side-group { font-size: 0.78rem; color: #9FB6C8 !important; margin: 14px 0 4px 4px; font-weight: 600; }
.side-empty { font-size: 0.85rem; color: #9FB6C8 !important; padding: 8px 4px; }

section[data-testid="stSidebar"] [data-testid="stTextInput"] [data-baseweb="input"],
section[data-testid="stSidebar"] [data-testid="stTextInput"] [data-baseweb="base-input"] {
    background: rgba(255,255,255,0.08) !important;
    border-radius: 12px !important;
    border-color: rgba(255,255,255,0.14) !important;
}
section[data-testid="stSidebar"] [data-testid="stTextInput"] input {
    background: transparent !important;
    color: #FFFFFF !important;
}
section[data-testid="stSidebar"] [data-testid="stTextInput"] input::placeholder {
    color: #9FB6C8 !important; opacity: 1;
}

/* history rows: any widget key starting with "hist" */
section[data-testid="stSidebar"] [class*="st-key-hist"] .stButton > button {
    background: transparent;
    color: #E6EEF5 !important;
    border: none;
    box-shadow: none;
    border-radius: 10px;
    font-weight: 500;
    justify-content: flex-start;
    text-align: left;
    padding: 0.45rem 0.7rem;
}
section[data-testid="stSidebar"] [class*="st-key-hist"] .stButton > button p {
    color: #E6EEF5 !important;
    text-align: left;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
section[data-testid="stSidebar"] [class*="st-key-hist"] .stButton > button:hover {
    background: rgba(255,255,255,0.10);
    transform: none;
    box-shadow: none;
}
section[data-testid="stSidebar"] [class*="st-key-histactive_"] .stButton > button {
    background: rgba(233,180,76,0.18);
    box-shadow: inset 3px 0 0 var(--marigold);
}
section[data-testid="stSidebar"] [class*="st-key-histdel_"] .stButton > button { opacity: 0.55; justify-content: center; }
section[data-testid="stSidebar"] [class*="st-key-histdel_"] .stButton > button:hover { opacity: 1; background: rgba(220,80,80,0.28); }

/* memory expander inside the sidebar */
section[data-testid="stSidebar"] [data-testid="stExpander"] {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 12px;
    margin-top: 14px;
}
section[data-testid="stSidebar"] [data-testid="stExpander"] summary { color: #FFFFFF !important; }

/* ---------- Attachments inside chat bubbles ---------- */
.file-chip {
    display: inline-block;
    background: #F1F6F5;
    border: 1px solid var(--line);
    border-radius: 999px;
    padding: 4px 12px;
    margin: 2px 6px 6px 0;
    font-size: 0.85rem;
    color: var(--ink);
}

/* ---------- Empty state ---------- */
.welcome {
    background: var(--card);
    border: 1px dashed #B7CFCB;
    border-radius: 18px;
    padding: 20px 24px;
    color: var(--muted);
}
.welcome b { color: var(--ink); }
.welcome ul { margin: 8px 0 0 0; padding-left: 20px; }
</style>"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# HEADER (HTML)
# ----------------------------------------------------------------------------
st.markdown(
    """
    <div class="hero">
        <h1>🏦 EMI & Loan Advisor</h1>
        <p>Tell me the loan you need and your monthly income. I'll work out the EMI,
        check what you can afford, and show which option costs the least interest.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

ALLOWED_FILES = ["png", "jpg", "jpeg", "webp", "pdf", "txt", "csv"]
FILE_NOTE = ("📎 I've saved your attachment to this chat, but I can't read the contents of images "
             "or documents yet. Please type the key details (monthly income, loan amount, rate, "
             "tenure) and I'll calculate.")


# ----------------------------------------------------------------------------
# CHAT SESSION HELPERS
# ----------------------------------------------------------------------------
def activate(chat_id, saved=None):
    """Make chat_id the active chat, restoring its saved memory if given."""
    agent = EMILoanAgent()
    if saved:
        agent.memory.update(saved["memory"])  # keeps defaults for any missing keys
    st.session_state.agent = agent
    st.session_state.chat_id = chat_id
    st.session_state.confirm_delete = None
    st.query_params["chat"] = chat_id          # so a browser refresh stays on this chat


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


# First load of this browser session: reopen the chat from the URL, else the latest chat
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
# HANDLE NEW INPUT FIRST (text + optional files/photos)
# ----------------------------------------------------------------------------
prompt = st.chat_input(
    "Ask about loan options or share your income...",
    accept_file="multiple",
    file_type=ALLOWED_FILES,
)
if prompt:
    if isinstance(prompt, str):
        text, files = prompt.strip(), []
    else:
        text, files = (prompt["text"] or "").strip(), list(prompt["files"] or [])

    saved_files = [store.save_attachment(chat_id, f.name, f.getvalue()) for f in files]

    if text:
        agent.run_step(text)             # appends the user message + assistant reply to hist
        if saved_files:
            hist[-2]["attachments"] = saved_files
            hist[-1]["content"] += "\n\n---\n" + FILE_NOTE
            hist[-1].setdefault("trace", []).append(
                f"[Files] Saved {len(saved_files)} attachment(s); file contents are not read.")
    elif saved_files:
        hist.append({"role": "user", "content": "", "attachments": saved_files})
        hist.append({"role": "assistant", "content": FILE_NOTE,
                     "trace": [f"[Files] Saved {len(saved_files)} attachment(s); file contents are not read."]})

    store.save_chat(chat_id, agent.memory)   # persist after every turn

# ----------------------------------------------------------------------------
# SIDEBAR: new chat, search, history, memory
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown('<div class="side-brand">🏦 Loan Advisor</div>', unsafe_allow_html=True)
    st.button("＋  New chat", key="newchat", on_click=cb_new_chat, use_container_width=True)

    query = st.text_input("Search chats", key="q_search", placeholder="Search chats",
                          label_visibility="collapsed")
    chats = store.search_chats(query)

    if not chats:
        st.markdown(
            '<div class="side-empty">No chats match your search.</div>' if query.strip()
            else '<div class="side-empty">Your chats will appear here once you send a message.</div>',
            unsafe_allow_html=True)

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
            b1.button("Delete", key=f"histyes_{c['id']}", on_click=cb_delete_chat,
                      args=(c["id"],), use_container_width=True)
            b2.button("Keep", key=f"histno_{c['id']}", on_click=cb_cancel_delete,
                      use_container_width=True)
            continue

        is_active = c["id"] == chat_id
        row_open, row_del = st.columns([6, 1])
        row_open.button(label, key=f"{'histactive' if is_active else 'hist'}_{c['id']}",
                        on_click=cb_open_chat, args=(c["id"],), use_container_width=True)
        row_del.button("🗑", key=f"histdel_{c['id']}", on_click=cb_ask_delete,
                       args=(c["id"],), help="Delete chat", use_container_width=True)

    with st.expander("🧠 Agent memory"):
        inc = agent.memory["monthly_income"]
        income_txt = "₹{:,.0f}".format(inc) if inc else "Not provided"
        yes_no = lambda v: "Yes" if v else "No"
        score = agent.memory.get("credit_score")
        st.markdown(
            f"""
            <div class="mem-card"><div class="label">Monthly income</div>
                <div class="value accent">{income_txt}</div></div>
            <div class="mem-card"><div class="label">No regular income</div>
                <div class="value">{yes_no(agent.memory['no_income'])}</div></div>
            <div class="mem-card"><div class="label">No credit history</div>
                <div class="value">{yes_no(agent.memory['no_credit'])}</div></div>
            <div class="mem-card"><div class="label">Credit score</div>
                <div class="value">{int(score) if score else 'Not provided'}</div></div>
            <div class="mem-card"><div class="label">Options stored</div>
                <div class="value">{len(agent.memory['computed_options'])}</div></div>
            """,
            unsafe_allow_html=True,
        )
    st.caption("Try: *I need a loan of 20 lakh*, *my salary is 80k*, *what if 7 years*, "
               "*10 lakh at 9% for 3 years and 5 years*")

# ----------------------------------------------------------------------------
# MAIN AREA: conversation (or a welcome card for an empty chat)
# ----------------------------------------------------------------------------
if not hist:
    st.markdown(
        """
        <div class="welcome">
            <b>Start a conversation.</b> You can type a question or attach a file or photo
            with the + button in the message box. For example:
            <ul>
                <li>I need a loan of 20 lakh</li>
                <li>My salary is 80k</li>
                <li>10 lakh at 9% for 3 years and 5 years</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

for msg in hist:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant" and msg.get("trace"):
            with st.expander("Agent thinking & tool calls", expanded=False):
                for log in msg["trace"]:
                    st.write(log)
        for att in msg.get("attachments") or []:
            path = store.attachment_path(att)
            if att.get("is_image") and path:
                st.image(str(path), width=260, caption=att["name"])
            else:
                st.markdown(
                    f'<span class="file-chip">📎 {html.escape(att["name"])} · {store.human_size(att.get("size", 0))}</span>',
                    unsafe_allow_html=True)
        if msg.get("content"):
            st.markdown(msg["content"])