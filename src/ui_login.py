import streamlit as st
import time
import datetime
import extra_streamlit_components as stx
from src.auth import login_user, create_token

def render_login(cookie_manager):
    # Avoid duplicate set_page_config if already set
    try:
        st.set_page_config(page_title="Login - Commeatus", page_icon="🔐", layout="centered")
    except Exception:
        pass

    st.title("🔐 Acesso Restrito")
    st.markdown("Entre com suas credenciais para acessar o sistema.")

    with st.form("login_form"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        
        submitted = st.form_submit_button("Entrar", type="primary")
        
        if submitted:
            if not username or not password:
                st.warning("Preencha todos os campos.")
            else:
                with st.spinner("Autenticando..."):
                    user = login_user(username, password)
                    time.sleep(1) # Feedback visual
                
                if user:
                    # 1. Update Session State
                    st.session_state.user = {
                        "id": user.id,
                        "username": user.username,
                        "name": user.name,
                        "role": user.role
                    }
                    
                    # 2. Generate and Set Token
                    token = create_token(user.username)
                    # Expires in 7 days (matches token exp)
                    cookie_manager.set("auth_token", token, key="set_auth_token", expires_at=datetime.datetime.utcnow() + datetime.timedelta(hours=1))
                    
                    st.success(f"Bem-vindo, {user.name or user.username}!")
                    time.sleep(1) # Give time for cookie to set
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")

    st.caption("© 2024 Commeatus System")
