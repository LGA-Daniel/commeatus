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

tab1, tab2, tab3 = st.tabs(["📥 Importar Pregões", "📊 Status do Banco", "⚡ Operações em Lote"])

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

with tab3:
    st.subheader("Operações em Lote (Itens e Resultados)")
    st.info("Selecione os pregões na tabela abaixo e escolha a operação desejada.")
    
    db_gen_items = get_db()
    db_items = next(db_gen_items)
    try:
        from src.models import ItemPregao, ItemResultado
        from sqlalchemy import func
        
        # 1. Load Pregoes
        pregoes = db_items.query(Pregao).order_by(Pregao.data_publicacao_pncp.desc()).limit(200).all()
        
        if not pregoes:
            st.warning("Nenhum pregão cadastrado.")
        else:
            # 2. Get Item Counts
            item_counts_query = db_items.query(
                ItemPregao.pregao_id, func.count(ItemPregao.id)
            ).group_by(ItemPregao.pregao_id).all()
            item_counts = {r[0]: r[1] for r in item_counts_query}
            
            # 3. Get Result Counts (Join ItemPregao -> ItemResultado)
            res_counts_query = db_items.query(
                ItemPregao.pregao_id, func.count(ItemResultado.id)
            ).select_from(ItemPregao).join(ItemResultado).group_by(ItemPregao.pregao_id).all()
            res_counts = {r[0]: r[1] for r in res_counts_query}
            
            # 3. Build DataFrame
            data_p = []
            
            # Helper: Select All Checkbox
            col_sel, col_empty = st.columns([0.2, 0.8])
            select_all = col_sel.checkbox("Selecionar Todos", value=False)
            
            for p in pregoes:
                # Parse content safely
                c = p.conteudo if isinstance(p.conteudo, dict) else {}
                if isinstance(p.conteudo, list) and len(p.conteudo) > 0: c = p.conteudo[0]
                elif isinstance(p.conteudo, str):
                    import json
                    try: c = json.loads(p.conteudo)
                    except: c = {}

                data_p.append({
                    "Selecionar": select_all,
                    "ID": p.id,
                    "Modalidade": c.get('modalidadeNome', '') or c.get('modalidadenome', '-'),
                    "Unidade": p.unidade_orgao or "-",
                    "Processo": f"{c.get('numeroCompra','')}/{c.get('anoCompra','')}",
                    "Objeto": c.get('objetoCompra', '') or c.get('objetocompra', '-'),
                    "Qtd Itens": item_counts.get(p.id, 0),
                    "Qtd Result.": res_counts.get(p.id, 0)
                })
            
            df_p = pd.DataFrame(data_p)
            
            edited_df = st.data_editor(
                df_p, 
                column_config={
                    "Selecionar": st.column_config.CheckboxColumn(required=True, width="small"),
                    "ID": st.column_config.NumberColumn(width="small"),
                    "Modalidade": st.column_config.TextColumn(width="medium"),
                    "Unidade": st.column_config.TextColumn(width="medium"),
                    "Processo": st.column_config.TextColumn(width="small"),
                    "Objeto": st.column_config.TextColumn(width="large", help="Descrição do objeto"),
                    "Qtd Itens": st.column_config.NumberColumn(width="small", help="Itens importados"),
                    "Qtd Result.": st.column_config.NumberColumn(width="small", help="Resultados importados")
                },
                disabled=["ID", "Modalidade", "Unidade", "Processo", "Objeto", "Qtd Itens", "Qtd Result."],
                hide_index=True,
                use_container_width=True
            )
            
            selected_rows = edited_df[edited_df["Selecionar"]]
            selected_ids = selected_rows["ID"].tolist()
            
            # --- Definitions for Dialogs ---
            
            @st.dialog("Importação de Itens")
            def run_batch_items_dialog(ids_to_process, all_pregoes):
                 st.write(f"Iniciando processamento de {len(ids_to_process)} pregões...")
                 progress_bar_i = st.progress(0)
                 status_text_i = st.empty()
                 
                 from src.workers.import_items import import_itens_pregao
                 
                 success_count = 0
                 error_count = 0
                 
                 for i, pid in enumerate(ids_to_process):
                     p_obj = next((x for x in all_pregoes if x.id == pid), None)
                     p_num = p_obj.numero_controle_pncp if p_obj else pid
                     
                     status_text_i.text(f"Processando Pregão {i+1}/{len(ids_to_process)} ({p_num})...")
                     
                     ok, msg, cnt = import_itens_pregao(pid)
                     if ok: success_count += 1
                     else: error_count += 1
                     
                     progress_bar_i.progress((i + 1) / len(ids_to_process))
                 
                 st.success(f"Concluído! {success_count} pregões processados com sucesso. {error_count} erros.")
                 if st.button("Fechar e Atualizar", key="close_items_dlg"): st.rerun()

            @st.dialog("Importação de Resultados")
            def run_batch_results_dialog(pids_to_check):
                st.write("Identificando itens elegíveis nos pregões selecionados...")
                from src.models import ItemPregao
                from sqlalchemy import text
                from src.workers.import_results import import_item_results
                
                db_gen_dlg = get_db()
                db_dlg = next(db_gen_dlg)
                
                try:
                    all_items_to_process = []
                    
                    for pid in pids_to_check:
                        targets = db_dlg.query(ItemPregao).filter(
                            ItemPregao.pregao_id == pid
                        ).filter(
                            text("Situacaocompraitemnome ILIKE '%homologado%' OR Situacaocompraitemnome ILIKE '%adjudicado%'")
                        ).all()
                        all_items_to_process.extend([t.id for t in targets])
                    
                    if not all_items_to_process:
                        st.warning("Nenhum item elegível (Homologado/Adjudicado) encontrado nos pregões selecionados.")
                    else:
                        st.info(f"Encontrados {len(all_items_to_process)} itens para buscar resultados.")
                        
                        prog_bar_r = st.progress(0)
                        stat_txt_r = st.empty()
                        
                        processed = 0
                        errs = 0
                        
                        for idx, item_id in enumerate(all_items_to_process):
                             stat_txt_r.text(f"Baixando item {idx+1}/{len(all_items_to_process)}...")
                             ok, m, c = import_item_results(item_id)
                             if not ok: errs += 1
                             processed += 1
                             prog_bar_r.progress(processed / len(all_items_to_process))
                        
                        st.success(f"Finalizado! {processed} itens verificados. {errs} falhas.")
                finally:
                    db_dlg.close()
                
                if st.button("Fechar", key="close_res_dlg"): st.rerun()
            
            # --- Action Buttons ---
            col_b1, col_b2, col_space = st.columns([1.5, 1.5, 4])
            
            with col_b1:
                # "Import Items" is safe to run always
                if st.button("📦 Importar Itens", type="primary", disabled=len(selected_ids)==0, use_container_width=True):
                    run_batch_items_dialog(selected_ids, pregoes)
            
            with col_b2:
                # Validation: Cannot run import results if pregao has 0 items
                ids_no_items = [pid for pid in selected_ids if item_counts.get(pid, 0) == 0]
                
                # Logic: If any selected pregao has 0 items, we block.
                # Or we filter them. User said "not allow". 
                # Strict: Disabled if selection includes ANY invalid one? No, better feedback is to filter.
                
                # Check valid candidates
                valid_ids_res = [pid for pid in selected_ids if pid not in ids_no_items]
                
                # Disable if no selection OR if NO valid IDs remain (all selected are 0 items)
                btn_res_disabled = len(selected_ids) == 0 or len(valid_ids_res) == 0
                
                # Button
                if st.button("📝 Importar Resultados", type="secondary", disabled=btn_res_disabled, use_container_width=True):
                     if len(ids_no_items) > 0:
                         # Mix of valid and invalid or all invalid (though button disabled if all invalid)
                         # If we are here, at least one is valid, but some might be invalid
                         st.warning(f"Atenção: {len(ids_no_items)} dos pregões selecionados não possuem itens e foram ignorados.")
                         run_batch_results_dialog(valid_ids_res)
                     else:
                         # All valid
                         run_batch_results_dialog(selected_ids)
                
                # Show hint if disabled due to selection
                if len(selected_ids) > 0 and len(valid_ids_res) == 0:
                    st.error("Selecione pregões com itens para importar resultados.")

    finally:
        db_items.close()

with tab2:
    st.subheader("Resumo da Base de Dados")
    
    if st.button("🛠️ Criar Tabelas Faltantes"):
        try:
             from src.database import engine
             from src.models import Base
             Base.metadata.create_all(bind=engine)
             st.success("Tabelas verificadas e criadas com sucesso!")
        except Exception as e:
             st.error(f"Erro ao criar tabelas: {e}")

    if st.button("Atualizar Estatísticas"):
        db_gen = get_db()
        db = next(db_gen)
        try:
            total_pregoes = db.query(Pregao).count()
            last_pregao = db.query(Pregao).order_by(Pregao.created_at.desc()).first()
            
            col_stat1, col_stat2 = st.columns(2)
            col_stat1.metric("Total de Pregões", total_pregoes)
            
            last_date = last_pregao.created_at.strftime("%d/%m/%Y %H:%M") if last_pregao and last_pregao.created_at else "N/A"
            
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
