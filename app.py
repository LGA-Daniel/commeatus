import streamlit as st
import extra_streamlit_components as stx
import time
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
                "id": user.id,
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
    time.sleep(1)
    st.rerun()

# --- Definição das Páginas ---
login_page = st.Page("views/0. Login.py", title="Login", icon="🔐")
home_page = st.Page("views/1. Home.py", title="Home", default=True)
pregoes_page = st.Page("views/3. Pregoes.py", title="Listar Aquisições/Contratações")
detalhes_page = st.Page("views/4. Detalhes Itens.py", title="Detalhes Itens", icon="📋")
db_page = st.Page("views/2. Test DBCONN.py", title="Diagnóstico de Banco", icon="🔌")

admin_page = st.Page("views/99. Admin Users.py", title="Gestão de Usuários", icon="👥")

scripts_page = st.Page("views/98. Admin Scripts.py", title="Gestão de Scripts", icon="⚙️")

# --- Lógica de Navegação ---
if st.session_state.user:
    # Authenticated User
    user_pages = [home_page, pregoes_page, detalhes_page]
    admin_tools = [db_page] 
    
    pages_dict = {
        "Navegação": [home_page, pregoes_page, detalhes_page],
        "Ferramentas": admin_tools
    }

    # Hack to hide the "Detalhes Itens" page from the sidebar but keep it accessible
    st.markdown("""
        <style>
            div[data-testid="stSidebarNav"] li:has(a[href*="Detalhes_Itens"]) {
                display: none;
            }
            /* Fallback if :has is not supported */
            div[data-testid="stSidebarNav"] a[href*="Detalhes_Itens"] {
                display: none;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Add Admin pages if role is admin
    if st.session_state.user['role'] == 'admin':
        pages_dict["Relatórios"] = [
            st.Page("views/5. Relatorio Fornecedores.py", title="Resultado por Fornecedor", icon="📊")
        ]
        pages_dict["Administração"] = [admin_page, scripts_page]
        
    pg = st.navigation(pages_dict)
    
    # Sidebar Logout
    with st.sidebar:
        st.write(f"Logado como: **{st.session_state.user['username']}**")
        if st.button("Sair", type="primary"):
            logout()
            
    # Cleanup Loop for Item Selection
    # If we are NOT on the details page, clear the selection
    # If we are NOT on the details page, clear the selection
    if pg.title != "Detalhes Itens":
        st.session_state.pop('selected_pregao_id', None)
        
    # Cleanup for "Relatorio Fornecedores"
    if pg.title != "Resultado por Fornecedor":
        keys_to_clear = ['active_report_id', 'export_pdf_data', 'export_csv_data', 'rep_years', 'rep_uasgs']
        for k in keys_to_clear:
            if k in st.session_state:
                del st.session_state[k]
            
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