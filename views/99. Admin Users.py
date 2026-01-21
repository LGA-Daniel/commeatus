import streamlit as st
import pandas as pd
from src.auth import create_user, get_all_users, delete_user, update_user, reset_password

st.set_page_config(page_title="Admin Users", page_icon="👥", layout="wide")

@st.dialog("➕ Adicionar Novo Usuário")
def add_user_dialog():
    with st.form("add_user_form"):
        new_username = st.text_input("Username*")
        new_name_add = st.text_input("Nome Completo")
        new_password = st.text_input("Senha*", type="password")
        new_role_add = st.selectbox("Perfil", ["user", "admin"])
        
        if st.form_submit_button("Criar Usuário"):
            if new_username and new_password:
                success, msg = create_user(new_username, new_password, new_name_add, new_role_add)
                if success:
                    st.success(f"Usuário {new_username} criado com sucesso!")
                    st.rerun()
                else:
                    st.error(f"Erro: {msg}")
            else:
                st.warning("Username e Senha são obrigatórios.")

# --- Header & Actions ---
col_header, col_btn = st.columns([3, 1])
col_header.title("👥 Gestão de Usuários")
if col_btn.button("➕ Novo Usuário", type="primary", use_container_width=True):
    add_user_dialog()

st.markdown("Adicione ou gerencie usuários do sistema.")

# --- List Users ---
st.subheader("Usuários Cadastrados")

@st.dialog("✏️ Editar Usuário")
def edit_user_dialog(user):
    st.write(f"Editando: **{user.username}**")
    with st.form("edit_dialog_form"):
        new_name = st.text_input("Nome", value=user.name or "")
        new_role = st.selectbox("Função", ["user", "admin"], index=0 if user.role == "user" else 1)
        
        if st.form_submit_button("Salvar Alterações", type="primary"):
            success, msg = update_user(user.username, name=new_name, role=new_role)
            if success:
                st.success("Atualizado com sucesso!")
                st.rerun()
            else:
                st.error(msg)

@st.dialog("🔑 Resetar Senha")
def reset_password_dialog(username):
    st.warning(f"Resetando a senha para: **{username}**")
    with st.form("reset_dialog_form"):
        new_pass = st.text_input("Nova Senha", type="password")
        confirm_pass = st.text_input("Confirmar Nova Senha", type="password")
        
        if st.form_submit_button("Definir Nova Senha", type="primary"):
            if new_pass and new_pass == confirm_pass and new_pass.strip():
                success, msg = reset_password(username, new_pass)
                if success:
                    st.success("Senha alterada!")
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.error("Senhas inválidas ou não conferem.")

@st.dialog("🗑️ Confirmar Exclusão")
def delete_user_dialog(username):
    st.write(f"Tem certeza que deseja excluir o usuário **{username}**?")
    st.warning("Esta ação não pode ser desfeita.")
    
    col1, col2 = st.columns(2)
    if col1.button("Sim, Excluir", type="primary", use_container_width=True):
        if delete_user(username):
            st.success("Usuário excluído.")
            st.rerun()
        else:
            st.error("Erro ao excluir.")
            
    if col2.button("Cancelar", use_container_width=True):
        st.rerun()

# --- List Users ---
st.subheader("Usuários Cadastrados")
users = get_all_users()

# List Header
cols = st.columns([1, 2, 2, 2, 2, 3])
headers = ["ID", "Usuário", "Nome", "Função", "Criado em", "Ações"]
for col, header in zip(cols, headers):
    col.markdown(f"**{header}**")

# List Rows
for u in users:
    cols = st.columns([1, 2, 2, 2, 2, 3])
    cols[0].write(u.id)
    cols[1].write(u.username)
    cols[2].write(u.name or "-")
    cols[3].write(u.role)
    cols[4].write(u.created_at.strftime('%Y-%m-%d %H:%M') if u.created_at else "-")
    
    with cols[5]:
        col_btns = st.columns(3)
        # Edit
        if col_btns[0].button("✏️", key=f"btn_edit_{u.id}", help="Editar"):
            edit_user_dialog(u)
            
        # Reset
        if col_btns[1].button("🔑", key=f"btn_reset_{u.id}", help="Resetar Senha"):
            reset_password_dialog(u.username)
            
        # Delete
        if u.username != "admin" and u.username != st.session_state.user['username']:
            if col_btns[2].button("🗑️", key=f"btn_del_{u.id}", help="Excluir"):
                delete_user_dialog(u.username)


