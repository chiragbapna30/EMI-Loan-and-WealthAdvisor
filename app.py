import streamlit as st
from agent import EMILoanAgent

st.set_page_config(page_title="EMI & Loan Advisor Agent", page_icon="🏦")
st.title("🏦 EMI & Loan Advisor Agent")

# Initialize agent in session state so memory persists
if "agent" not in st.session_state:
    st.session_state.agent = EMILoanAgent()

# Display chat history from agent memory
for msg in st.session_state.agent.memory["conversation_history"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User Input
if prompt := st.chat_input("Ask about loan options or share your income..."):
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Run agent loop
    result = st.session_state.agent.run_step(prompt)
    
    # Display trace step logs
    with st.status("Agent Thinking & Executing Tools...", expanded=False):
        for log in result["trace"]:
            st.write(log)
            
    # Display agent response
    with st.chat_message("assistant"):
        st.markdown(result["response"])