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
# COMPRETo make a hidden or non-visible sidebar appear, the issue usually comes down to CSS display properties, HTML layout structure, or missing state logic in JavaScript. 

Here are the most common fixes based on standard web implementations:

### 1. Fix CSS Visibility & Display
Check if your CSS is hiding the sidebar via `display: none;`, `visibility: hidden;`, or off-screen transforms:

```css
/* Ensure the sidebar element itself is visible */
.sidebar {
  display: block !important; /* Forces layout rendering */
  visibility: visible !important;
  opacity: 1 !important;
  z-index: 1000; /* Keeps it above other layered content */
}

/* If using off-screen sliding mechanics */
.sidebar.hidden {
  transform: translateX(-100%); /* Hides off-screen */
}

.sidebar.active {
  transform: translateX(0); /* Brings it back into view */
}
