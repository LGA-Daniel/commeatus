import streamlit as st
import extra_streamlit_components as stx
from src.ui_login import render_login

# Retrieve cookie manager from session state (initialized in app.py)
if "cookie_manager" in st.session_state:
    cookie_manager = st.session_state.cookie_manager
else:
    # Fallback/Safety
    cookie_manager = stx.CookieManager(key="auth_cookie_manager")

render_login(cookie_manager)
