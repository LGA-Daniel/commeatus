import streamlit as st
import pandas as pd
from src.database import get_engine, get_db
from src.models import Pregao, ItemPregao

st.set_page_config(page_title="Detalhes dos Itens", page_icon="📋", layout="wide")

padding_style = """
    <style>
    .stMain {
        padding-top: 2rem;
    }
    div[role="dialog"][aria-modal="true"] {
        max-width: 60vw !important;
        width: 60vw !important;
    }
    </style>
"""
st.markdown(padding_style, unsafe_allow_html=True)

if st.button("⬅️ Voltar para Lista"):
    st.switch_page("views/3. Pregoes.py")

pregao_id = st.session_state.get('selected_pregao_id')

if not pregao_id:
    st.warning("Nenhum pregão selecionado.")
    st.stop()

engine = get_engine()

# Fetch Pregao Details
try:
    with next(get_db()) as db:
        pregao = db.query(Pregao).filter(Pregao.id == pregao_id).first()
        
        if not pregao:
            st.error("Pregão não encontrado na base de dados.")
            st.stop()
            
        c_title, c_link, c_btn = st.columns([0.6, 0.2, 0.2])
        c_title.title(f"📋 Itens do Pregão {pregao.numero_controle_pncp}")
        
        # Try to extract link
        link_pncp = None
        try:
            dados = pregao.conteudo
            if isinstance(dados, str):
                import json
                dados = json.loads(dados)
            if isinstance(dados, list) and dados:
                dados = dados[0]
            if isinstance(dados, dict):
                link_pncp = dados.get('linkSistemaOrigem') or dados.get('linksistemaorigem')
        except:
            pass
            
        if link_pncp:
            c_link.link_button("🔗 Abrir no PNCP", link_pncp)
        
        # Modal for Execution with Feedback (Same as Pregoes.py)
        @st.dialog("Sincronização de Itens")
        def run_import_dialog(pregao_id):
            st.write("Conectando à API PNCP...")
            
            status_container = st.empty()
            
            with status_container.status("Processando...", expanded=True) as status:
                st.write("Baixando dados...")
                from src.workers.import_items import import_itens_pregao
                success, msg, count = import_itens_pregao(pregao_id)
                
                if success:
                    status.update(label="Concluído!", state="complete", expanded=False)
                else:
                    status.update(label="Erro!", state="error", expanded=False)
                    
            if success:
                st.success(f"{msg}")
                st.info(f"Itens processados: {count}")
            else:
                st.error(f"Falha na importação: {msg}")
                
            if st.button("Fechar e Atualizar", type="primary"):
                st.rerun()

        @st.dialog("Importação em Lote")
        def run_batch_results(pregao_id):
            st.write("Identificando itens homologados...")
            
            # Find target items
            with next(get_db()) as db:
                from sqlalchemy import text
                # We look for items that are likely closed/finished
                # Use text() because 'situacaocompraitemnome' is a dynamic column not in the ORM model
                targets = db.query(ItemPregao).filter(
                    ItemPregao.pregao_id == pregao_id
                ).filter(
                    text("Situacaocompraitemnome ILIKE '%homologado%' OR Situacaocompraitemnome ILIKE '%adjudicado%'")
                ).all()
                
                items_to_process = [t.id for t in targets]
            
            if not items_to_process:
                st.warning("Nenhum item com situação 'Homologado' ou 'Adjudicado' encontrado.")
                if st.button("Fechar"): st.rerun()
                return

            st.info(f"Encontrados {len(items_to_process)} itens para processar.")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            processed = 0
            errors = 0
            
            from src.workers.import_results import import_item_results
            
            for idx, item_id in enumerate(items_to_process):
                status_text.text(f"Processando item {idx+1}/{len(items_to_process)} (ID: {item_id})...")
                ok, msg, cnt = import_item_results(item_id)
                if not ok: errors += 1
                processed += 1
                progress_bar.progress(processed / len(items_to_process))
            
            st.success(f"Processamento concluído! {processed} itens verificados.")
            if errors > 0:
                st.warning(f"{errors} itens apresentaram erro ou sem dados.")
            
            if st.button("Concluir", type="primary"):
                st.rerun()

        c_btn.button("🔄 Atualizar Itens", type="primary", on_click=run_import_dialog, args=(pregao_id,))
        c_btn.button("📥 Baixar Resultados", on_click=run_batch_results, args=(pregao_id,), help="Baixar resultados dos itens homologados")
        
        # Pregao Header
        with st.container(border=True):
            cols = st.columns(4)
            cols[0].metric("Unidade", pregao.unidade_orgao or "-")
            cols[1].metric("CNPJ", pregao.cnpj_orgao or "-")
            cols[2].metric("Data Publicação", pregao.data_publicacao_pncp.strftime("%d/%m/%Y") if pregao.data_publicacao_pncp else "-")
            
            # Extract additional info if possible
            total_items = db.query(ItemPregao).filter(ItemPregao.pregao_id == pregao_id).count()
            cols[3].metric("Total de Itens", total_items)

        st.subheader("Itens Licitados")
        
        # Modal for Item Details
        @st.dialog("Detalhes do Item", width="large")
        def show_item_details(row_data):
            st.subheader(f"Item {row_data.get('numero_item', '?')} - {row_data.get('descricao', 'N/A')}")
            
            # Identify "core" fields vs "extra" fields
            exclude_keys = ['id', 'pregao_id', 'conteudo', 'created_at']
            
            # Display core/flat fields first
            flat_data = {k: v for k, v in row_data.items() if k not in exclude_keys}
            
            # Grid layout for flat fields
            if flat_data:
                st.markdown("##### Dados Principais")
                cols = st.columns(2)
                idx = 0
                for k, v in flat_data.items():
                    with cols[idx % 2]:
                        st.text_input(k.replace("_", " ").title(), str(v), disabled=True)
                    idx += 1
            
            st.divider()
            
            # Display raw JSON content if available
            conteudo = row_data.get('conteudo')
            if conteudo:
                with st.expander("Conteúdo JSON Completo (API)", expanded=False):
                    if isinstance(conteudo, str):
                        try:
                            import json
                            st.json(json.loads(conteudo))
                        except:
                            st.text(conteudo)
                    else:
                        st.json(conteudo)

        # Modal for Result Details
        @st.dialog("Detalhes do Resultado", width="large")
        def show_result_details(item_id, conteudo_result):
            st.subheader("Resultado do Item")
            
            col_top_1, col_top_2 = st.columns([0.7, 0.3])
            if col_top_2.button("🔄 Atualizar Resultado"):
                 with st.spinner("Consultando API PNCP..."):
                     from src.workers.import_results import import_item_results
                     success, msg, count = import_item_results(item_id)
                     if success:
                         st.success("Atualizado!")
                         # Refresh data in-place to keep modal open
                         from src.models import ItemResultado
                         with next(get_db()) as db: # Use get_db from top-level import
                             res = db.query(ItemResultado).filter(ItemResultado.item_pregao_id == item_id).first()
                             if res:
                                 conteudo_result = res.conteudo
                     else:
                         st.error(msg)
            
            # Use raw JSON content
            data_dict = {}
            if isinstance(conteudo_result, str):
                import json
                try: data_dict = json.loads(conteudo_result)
                except: data_dict = {"raw": conteudo_result}
            elif isinstance(conteudo_result, dict):
                data_dict = conteudo_result
            
            # Display important fields in a grid
            if data_dict:
                # Identify likely important fields
                # Filter out complex objects for the top grid
                simple_fields = {k: v for k, v in data_dict.items() if isinstance(v, (str, int, float, bool)) and v is not None}
                
                if simple_fields:
                    st.markdown("##### Dados Principais")
                    cols = st.columns(2)
                    idx = 0
                    for k, v in simple_fields.items():
                        with cols[idx % 2]:
                             st.text_input(k.replace("_", " ").title(), str(v), disabled=True)
                        idx += 1
                
                st.divider()
                with st.expander("Conteúdo JSON Completo", expanded=False):
                    st.json(data_dict)

        # Modal for Fetching Results
        @st.dialog("Sincronização de Resultados")
        def fetch_result_dialog(item_id):
            st.write("Consultando resultados no PNCP...")
            status_container = st.empty()
            
            with status_container.status("Processando...", expanded=True) as status:
                st.write("Acessando API...")
                from src.workers.import_results import import_item_results
                success, msg, count = import_item_results(item_id)
                
                if success:
                    status.update(label="Concluído!", state="complete", expanded=False)
                else:
                    status.update(label="Erro!", state="error", expanded=False)
                    
            if success:
                st.success(f"{msg}")
                if count > 0:
                    st.info(f"{count} registros de resultado encontrados.")
                else:
                    st.warning("Nenhum resultado disponível (204).")
            else:
                st.error(f"Falha: {msg}")
                
            if st.button("Fechar e Atualizar", type="primary", key="btn_close_res_dlg"):
                st.rerun()

        # Load all items with all columns
        query = f"""
            SELECT *
            FROM itens_pregao
            WHERE pregao_id = {pregao_id}
            ORDER BY numero_item ASC
        """
        
        df_items = pd.read_sql(query, engine)
        
        # Load Existing Results Map (item_id -> content/true)
        from src.models import ItemResultado
        items_with_results = {}
        try:
            results_query = f"""
                SELECT item_pregao_id, conteudo 
                FROM itens_resultados 
                WHERE item_pregao_id IN ({','.join([str(x) for x in df_items['id'].tolist()] + [str(0)])})
            """
            results_df = pd.read_sql(results_query, engine)
            for _, r in results_df.iterrows():
                items_with_results[r['item_pregao_id']] = r['conteudo']
        except:
            pass # Table might not exist yet
        
        if not df_items.empty:
            # Table Header
            cols = st.columns([1, 4, 1.8, 1.3, 1.5, 1.5, 1.5]) 
            headers = ["Item", "Descrição", "Situação", "Qtd", "Val. Unit", "Val. Total", "Ações"]
            
            st.markdown("""
            <div style="border-bottom: 2px solid #ddd; padding-bottom: 5px; margin-bottom: 10px; font-weight: bold;">
            """, unsafe_allow_html=True)
            for col, h in zip(cols, headers):
                col.write(h)
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Helper for safe float conversion
            def safe_float(val):
                try:
                    if pd.isna(val) or val == "": return None
                    return float(str(val).replace(",", "."))
                except:
                    return None

            # Table Rows
            for _, row in df_items.iterrows():
                row_id = row.get('id', 0)
                situacao = str(row.get('situacaocompraitemnome', '')).lower()
                has_result = row_id in items_with_results
                
                # Extract values safely
                c = st.columns([1, 4, 1.8, 1.3, 1.5, 1.5, 1.5])
                
                c[0].write(row.get('numero_item', '-'))
                c[1].write(row.get('descricao', '-'))
                c[2].write(row.get('situacaocompraitemnome', '-'))
                
                qtd = safe_float(row.get('quantidade'))
                c[3].write(f"{qtd:.2f}" if qtd is not None else "-")
                
                v_unit = safe_float(row.get('valor_unitario') or row.get('Valorunitario') or row.get('valorunitario'))
                c[4].write(f"R$ {v_unit:,.2f}" if v_unit is not None else "-")
                
                v_total = safe_float(row.get('Valortotal') or row.get('valortotal') or row.get('valor_total'))
                c[5].write(f"R$ {v_total:,.2f}" if v_total is not None else "-")
                
                # Action Buttons
                col_act = c[6]
                
                # Grid for buttons
                c_a1, c_a2 = col_act.columns(2)
                
                # 1. View Item Detail
                if c_a1.button("🔍", key=f"btn_item_{row_id}", help="Ver Detalhes do Item"):
                    show_item_details(row)
                
                # 2. Result Button (only if applicable)
                if has_result:
                     if c_a2.button("📋", key=f"btn_view_res_{row_id}", help="Ver Resultado Homologado", type="secondary"):
                         show_result_details(row_id, items_with_results[row_id])
                elif "homologado" in situacao or "adjudicado" in situacao:
                     if c_a2.button("📥", key=f"btn_fetch_res_{row_id}", help="Buscar Resultado na API"):
                         fetch_result_dialog(row_id)
                
                st.markdown("<hr style='margin: 5px 0; opacity: 0.3;'>", unsafe_allow_html=True)
        else:
            st.info("Nenhum item encontrado para este pregão.")

except Exception as e:
    st.error(f"Erro ao carregar itens: {e}")
