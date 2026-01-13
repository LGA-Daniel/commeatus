import streamlit as st
import psycopg2
import os

st.set_page_config(page_title="Teste DB", page_icon="🔌")

st.header("Verificação de Conexão: PostgreSQL")

# Pegamos as credenciais das variáveis de ambiente do Docker
db_host = os.getenv('DB_HOST', '192.168.0.10:5432')
db_name = os.getenv('DB_NAME', 'commeatus_db')
db_user = os.getenv('DB_USER', 'postgres')
db_pass = os.getenv('DB_PASS', 'postgres')

st.write(f"Tentando conectar em: **{db_host}** (Database: {db_name})")

if st.button("Testar Conexão Agora"):
    try:
        conn = psycopg2.connect(
            host=db_host,
            database=db_name,
            user=db_user,
            password=db_pass
        )
        st.success("✅ Conexão BEM SUCEDIDA!")
        
        # Teste extra: Buscar versão do banco
        cur = conn.cursor()
        cur.execute("SELECT version();")
        db_version = cur.fetchone()
        st.info(f"Versão do Banco: {db_version[0]}")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        st.error(f"❌ Falha na conexão: {e}")
        st.warning("Dica: Verifique se o container 'commeatus_db' está rodando com 'docker ps'")