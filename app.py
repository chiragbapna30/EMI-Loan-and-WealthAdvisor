import html
import pandas as pd
import plotly.express as px
import streamlit as st

from agent import EMILoanAgent, generate_amortization_schedule, inr
import chat_store as store

st.set_page_config(page_title="EMI & Loan Advisor Agent", page_icon="🏦", layout="centered")

# ----------------------------------------------------------------------------
# CUSTOM CSS
# ----------------------------------------------------------------------------
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

:root {
    --ink: #0F2A43;
    --ink-soft: #1C3F5E;
    --teal: #0E7C7B;
    --mist: #F1F6F5;
    --marigold: #E9B44C;
    --slate: #1B2B3A;
}

html, body, [class*="css"], .stApp, .stMarkdown {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    color: var(--slate);
}

.hero {
    background: linear-gradient(135deg, var(--ink) 0%, var(--ink-soft) 60%, var(--teal) 130%);
    border-radius: 20px;
    padding: 24px 28px;
    margin-bottom: 1.2rem;
    box-shadow: 0 10px 25px rgba(15, 42, 67, 0.15);
    border-left: 6px solid var(--marigold);
}
.hero h1 {
    font-family: 'Fraunces', Georgia, serif !important;
    color: #FFFFFF !important;
    font-size: 2rem;
    margin: 0 0 4px 0;
}
.hero p {
    color: #C9DCE8 !important;
    margin: 0;
    font-size: 0.95rem;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# HEADER & HERO
# ----------------------------------------------------------------------------
st.markdown(
    """
    <div class="hero">
        <h1>🏦 EMI & Loan Advisor Agent</h1>
        <p>Smart financial guidance, loan comparison, and interactive repayment schedules.</p>
    </div>
    """,
    unsafe_allow_html=True
)

# ----------------------------------------------------------------------------
# SUGGESTION CHIPS (Quick Prompts)
# ----------------------------------------------------------------------------
st.subheader("💡 Quick Prompts")
col1, col2, col3, col4 = st.columns(4)

suggested_prompt = None
if col1.button("📌 20 L @ 8.5% for 5 yrs"):
    suggested_prompt = "I need a loan of 20 lakh at 8.5% interest rate for 5 years. My salary is 80000."
if col2.button("📊 Compare 3 vs 5 Years"):
    suggested_prompt = "Compare 10 lakh loan at 9% for 3 years and 5 years"
if col3.button("📄 Home Loan Documents"):
    suggested_prompt = "What documents are required for a home loan application?"
if col4.button("📈 Improve CIBIL Score"):
    suggested_prompt = "How can I improve my CIBIL credit score fast?"

# ----------------------------------------------------------------------------
# CHAT LOGIC & HISTORY
# ----------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# Initialize agent
agent = EMILoanAgent()

# Render chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        
        # If memory contains computed options, render Chart & CSV Export
        if msg.get("computed_options"):
            opts = msg["computed_options"]
            
            # --- Interactive Amortization Chart ---
            with st.expander("📈 View Interactive Amortization Schedule Chart", expanded=False):
                selected_opt = st.selectbox(
                    "Select Option to Visualize:",
                    options=range(len(opts)),
                    format_func=lambda i: f"Option {i+1}: {inr(opts[i]['amount'])} @ {opts[i]['rate_annual']}% ({opts[i]['months']}m)"
                )
                opt_data = opts[selected_opt]
                schedule = generate_amortization_schedule(
                    opt_data["amount"], opt_data["rate_annual"], opt_data["months"]
                )
                df_schedule = pd.DataFrame(schedule)
                
                fig = px.bar(
                    df_schedule, 
                    x="Month", 
                    y=["Principal Paid", "Interest Paid"], 
                    title=f"Repayment Breakdown for Option {selected_opt + 1}",
                    labels={"value": "Amount (₹)", "variable": "Component"},
                    color_discrete_map={"Principal Paid": "#0E7C7B", "Interest Paid": "#E9B44C"}
                )
                st.plotly_chart(fig, use_container_width=True)

            # --- CSV Download Option ---
            with st.expander("📥 Export Loan Comparison Data", expanded=False):
                df_opts = pd.DataFrame(opts)
                csv_bytes = df_opts.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Comparison Summary (CSV)",
                    data=csv_bytes,
                    file_name="loan_comparison_summary.csv",
                    mime="text/csv"
                )

# User Input (either typed or clicked from prompt suggestion chips)
user_query = st.chat_input("Type your loan question here...") or suggested_prompt

if user_query:
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.write(user_query)

    # Run agent step
    response = agent.run_step(user_query)
    bot_msg = {
        "role": "assistant", 
        "content": response,
        "computed_options": agent.memory.get("computed_options")
    }
    st.session_state.messages.append(bot_msg)
    st.rerun()
