import streamlit as st
import psycopg2
import pandas as pd

st.set_page_config(page_title="Teste de Conexão", page_icon="🔌")

st.header("🔌 Diagnóstico de Conexão (Modo Seguro)")
st.markdown("Verificação de acesso usando credenciais do **Secrets Manager**.")

# 1. Validação da existência do arquivo secrets.toml
if "database" not in st.secrets:
    st.error("❌ Arquivo `.streamlit/secrets.toml` não encontrado ou seção [database] ausente.")
    st.info("Crie o arquivo com as chaves: host, port, dbname, user, password.")
    st.stop()

# Recupera as configurações (sem mostrar a senha)
db_config = st.secrets["database"]

# Mostra os parâmetros de conexão (mas mascara a senha)
with st.expander("Verificar Parâmetros de Configuração", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Host", value=db_config.get("host"), disabled=True)
        st.text_input("Database", value=db_config.get("dbname"), disabled=True)
    with col2:
        st.text_input("Usuário", value=db_config.get("user"), disabled=True)
        st.text_input("Senha", value="********", disabled=True)

st.divider()

# 2. Teste de Conexão
if st.button("🔄 Testar Conexão Agora", type="primary"):
    status_container = st.status("Iniciando tentativa de conexão...", expanded=True)
    
    try:
        # Abertura da conexão
        status_container.write("📡 Tentando contactar o PostgreSQL...")
        conn = psycopg2.connect(
            host=db_config["host"],
            database=db_config["dbname"],
            user=db_config["user"],
            password=db_config["password"],
            port=db_config.get("port", 5432)
        )
        status_container.write("✅ Socket conectado com sucesso!")
        
        # Criação do cursor
        cur = conn.cursor()
        
        # Teste 1: Versão do Banco
        status_container.write("🔍 Verificando versão do servidor...")
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        
        # Teste 2: Usuário Atual e Permissões
        status_container.write("👤 Verificando identidade do usuário...")
        cur.execute("SELECT current_user, current_database();")
        user_info = cur.fetchone()
        current_user = user_info[0]
        current_db = user_info[1]

        # Fechamento
        cur.close()
        conn.close()
        
        status_container.update(label="Conexão Estabelecida com Sucesso!", state="complete", expanded=False)
        
        # Resultados Finais
        st.success("O sistema está 100% operacional.")
        
        st.metric(label="Banco de Dados", value=current_db)
        st.metric(label="Usuário Conectado", value=current_user, 
                 delta="Correto" if current_user == db_config["user"] else "Diferente do Configurado")
        
        st.caption(f"Versão do Core: {version}")

    except psycopg2.Error as e:
        status_container.update(label="Falha na Conexão", state="error", expanded=True)
        st.error(f"Erro de Banco de Dados: {e}")
        st.warning("Verifique se o container 'db' está rodando e se a senha no secrets.toml está correta.")
        
    except Exception as e:
        status_container.update(label="Erro Genérico", state="error")
        st.error(f"Erro inesperado: {e}")