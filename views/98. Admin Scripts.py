import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# Ensure src can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.workers.import_pregoes import run_import_pregoes
from src.database import get_db
from src.models import Pregao

st.set_page_config(page_title="Gestão de Scripts", page_icon="⚙️", layout="wide")

st.title("⚙️ Gestão de Scripts e Rotinas")
st.markdown("Execute rotinas de manutenção e importação de dados manualmente.")

tab1, tab2 = st.tabs(["📥 Importar Pregões", "📊 Status do Banco"])

with tab1:
    st.subheader("Importação de Pregões PNCP")
    st.info("Esta rotina consulta a API do PNCP para os CNPJs configurados e insere novos registros no banco de dados.")

    col1, col2 = st.columns(2)
    
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    
    with col1:
        data_inicial = st.date_input("Data Inicial", value=yesterday)
    with col2:
        data_final = st.date_input("Data Final", value=today)

    if st.button("🚀 Executar Importação", type="primary"):
        if data_inicial > data_final:
            st.error("A Data Inicial não pode ser maior que a Data Final.")
        else:
            status_container = st.status("Iniciando importação...", expanded=True)
            log_container = st.empty()
            logs = []

            def update_progress(msg):
                logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {msg}")
                # Keep only last 10 logs visible to avoid clutter
                log_text = "\n".join(logs[-10:])
                status_container.write(msg)
                # print(msg) # Optional console log

            # Convert dates to YYYYMMDD string
            d_ini_str = data_inicial.strftime("%Y%m%d")
            d_fim_str = data_final.strftime("%Y%m%d")

            try:
                total, errors = run_import_pregoes(d_ini_str, d_fim_str, progress_callback=update_progress)
                
                status_container.update(label="Importação Concluída!", state="complete", expanded=False)
                
                if total > 0:
                    st.success(f"Sucesso! {total} novos pregões importados.")
                else:
                    st.warning("Nenhum novo registro encontrado para o período.")
                
                if errors:
                    st.error(f"{len(errors)} erros ocorreram:")
                    for err in errors:
                        st.write(err)
                        
            except Exception as e:
                status_container.update(label="Erro Fatal", state="error")
                st.error(f"Erro crítico: {e}")

with tab2:
    st.subheader("Resumo da Base de Dados")
    
    if st.button("Atualizar Estatísticas"):
        db_gen = get_db()
        db = next(db_gen)
        try:
            total_pregoes = db.query(Pregao).count()
            last_pregao = db.query(Pregao).order_by(Pregao.created_at.desc()).first()
            
            col_stat1, col_stat2 = st.columns(2)
            col_stat1.metric("Total de Pregões", total_pregoes)
            
            last_date = last_pregao.created_at.strftime("%d/%m/%Y %H:%M") if last_pregao else "N/A"
            col_stat2.metric("Última Importação", last_date)
            
            # Show recent records
            st.write("Últimos 5 registros:")
            recent = db.query(Pregao).order_by(Pregao.created_at.desc()).limit(5).all()
            data = []
            for r in recent:
                data.append({
                    "ID": r.id,
                    "Numero PNCP": r.numero_controle_pncp,
                    "Data Publicação": r.data_publicacao_pncp,
                    "Importado Em": r.created_at
                })
            st.dataframe(pd.DataFrame(data), use_container_width=True)
            
        finally:
            db.close()
