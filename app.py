import streamlit as st
import extra_streamlit_components as stx
from src.auth import init_db_and_admin_if_needed, validate_token

# Initialize Database and Admin
# Connect to DB once
db_init = st.cache_resource(init_db_and_admin_if_needed)()

# --- Cookie Manager ---
# Key identifies the component instance
cookie_manager = stx.CookieManager(key="auth_cookie_manager")
if "cookie_manager" not in st.session_state:
    st.session_state.cookie_manager = cookie_manager

# --- Session State Management ---
if "user" not in st.session_state:
    st.session_state.user = None

# Check for existing token in cookies if user is not logged in
if st.session_state.user is None:
    # We need to sleep briefly to ensure cookies are loaded? 
    # Usually stx handles it, but might require a rerun if it's the very first mount.
    # get_all() triggers the component to read cookies.
    cookies = cookie_manager.get_all()
    token = cookies.get("auth_token")
    if token:
        user = validate_token(token)
        if user:
            st.session_state.user = {
                "username": user.username,
                "name": user.name,
                "role": user.role
            }
            # Force rerun to apply authentication state immediately
            st.rerun()

def logout():
    st.session_state.user = None
    # Delete cookie
    cookie_manager.delete("auth_token")
    st.rerun()

# --- Definição das Páginas ---
login_page = st.Page("views/0. Login.py", title="Login", icon="🔐")
home_page = st.Page("views/1. Home.py", title="Home", default=True)
db_page = st.Page("views/2. Test DBCONN.py", title="Diagnóstico de Banco", icon="🔌")
admin_page = st.Page("views/99. Admin Users.py", title="Gestão de Usuários", icon="👥")

# --- Lógica de Navegação ---
if st.session_state.user:
    # Authenticated User
    user_pages = [home_page]
    admin_tools = [db_page] 
    
    pages_dict = {
        "Navegação": user_pages,
        "Ferramentas": admin_tools
    }
    
    # Add Admin pages if role is admin
    if st.session_state.user['role'] == 'admin':
        pages_dict["Administração"] = [admin_page]
        
    pg = st.navigation(pages_dict)
    
    # Sidebar Logout
    with st.sidebar:
        st.write(f"Logado como: **{st.session_state.user['username']}**")
        if st.button("Sair", type="primary"):
            logout()
            
    pg.run()
            
else:
    # Not Authenticated
    # We define ALL pages here to avoid 404 on refresh (Run 1)
    # But we hide the navigation because the user shouldn't see it yet.
    # If the cookie check passes (Run 2/3), we'll switch to the authenticated block.
    pg = st.navigation([login_page, home_page, db_page, admin_page], position="hidden")
    
    # If the user is trying to access a restricted page (not login),
    # we still show the LOGIN page content, but keep the URL /... intact.
    # We call the UI logic directly.
    from src.ui_login import render_login
    render_login(cookie_manager)