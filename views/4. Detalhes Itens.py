import streamlit as st
import pandas as pd
from src.database import get_engine, get_db
from src.models import Pregao, ItemPregao
from src.ui_item_details import show_item_details, show_result_details, fetch_result_dialog

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



pregao_id = st.session_state.get('selected_pregao_id')

if not pregao_id:
    st.warning("Nenhum pregão selecionado.")
    if st.button("⬅️ Voltar para a Lista"):
        st.switch_page("views/3. Pregoes.py")
    st.stop()

engine = get_engine()

# Fetch Pregao Details
try:
    with next(get_db()) as db:
        pregao = db.query(Pregao).filter(Pregao.id == pregao_id).first()
        
        if not pregao:
            st.error("Pregão não encontrado na base de dados.")
            st.stop()
            

        
        # Try to extract link
        # Extract JSON Content safely
        dados_json = {}
        link_pncp = None
        try:
            raw_c = pregao.conteudo
            if isinstance(raw_c, str):
                import json
                dados_json = json.loads(raw_c)
            elif isinstance(raw_c, (dict, list)):
                dados_json = raw_c
                
            if isinstance(dados_json, list) and dados_json:
                dados_json = dados_json[0]
                
            if isinstance(dados_json, dict):
                link_pncp = dados_json.get('linkSistemaOrigem') or dados_json.get('linksistemaorigem')
        except:
            pass
            

            
        # Prepare Context for Items
        pregao_ctx = {
            "numero": dados_json.get('numeroCompra') or dados_json.get('numerocompra'),
            "ano": dados_json.get('anoCompra') or dados_json.get('anocompra'),
            "uasg": pregao.unidade_orgao
        }
        
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
                import time
                time.sleep(2)
                st.rerun()
            else:
                st.error(f"Falha na importação: {msg}")
                if st.button("Fechar", type="primary"):
                    st.rerun()

        @st.dialog("Importação em Lote")
        def run_batch_results(pregao_id):
            # Unique session key for this operation
            session_key = f"batch_import_state_{pregao_id}"
            
            # Initialize state if needed
            if session_key not in st.session_state:
                # Start immediately
                st.session_state[session_key] = {"status": "running", "results": None}

            state = st.session_state[session_key]

            st.write("Identificando itens homologados...")
            
            # Find target items
            items_to_process = []
            try:
                with next(get_db()) as db:
                    from sqlalchemy import text
                    targets = db.query(ItemPregao).filter(
                        ItemPregao.pregao_id == pregao_id
                    ).filter(
                        text("Situacaocompraitemnome ILIKE '%homologado%' OR Situacaocompraitemnome ILIKE '%adjudicado%'")
                    ).all()
                    
                    items_to_process = [t.id for t in targets]
            except Exception as e:
                st.error(f"Erro ao buscar itens: {e}")
                return
            
            if not items_to_process:
                st.warning("Nenhum item com situação 'Homologado' ou 'Adjudicado' encontrado.")
                if st.button("Fechar"): 
                     if session_key in st.session_state: del st.session_state[session_key]
                     st.rerun()
                return

            st.info(f"Encontrados {len(items_to_process)} itens para processar.")
            
            # State Machine
            if state["status"] == "running":
                # Use status container for better UI
                with st.status("Processando Resultados...", expanded=True) as status:
                    st.write("Iniciando download...")
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    processed = 0
                    errors = 0
                    
                    from src.workers.import_results import import_item_results
                    
                    # Perform the loop
                    total = len(items_to_process)
                    for idx, item_id in enumerate(items_to_process):
                        status_text.text(f"Item {idx+1}/{total} (ID: {item_id})")
                        ok, msg, cnt = import_item_results(item_id)
                        if not ok: 
                            st.write(f"❌ Item {item_id}: {msg}")
                            errors += 1
                        processed += 1
                        progress_bar.progress(processed / total)
                    
                    status.update(label="Processamento Concluído!", state="complete", expanded=False)
                
                # Save results to state and update status
                st.session_state[session_key]["results"] = {
                    "processed": processed,
                    "errors": errors
                }
                st.session_state[session_key]["status"] = "done"
                st.rerun()
                
            elif state["status"] == "done":
                res = state.get("results", {})
                st.success(f"Operação finalizada! {res.get('processed', 0)} itens verificados.")
                
                if res.get('errors', 0) > 0:
                    st.warning(f"{res.get('errors')} itens apresentaram falha. Verifique os logs acima.")
                
                # Wait a bit longer so user can read
                import time
                time.sleep(4)
                del st.session_state[session_key]
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
            # Safe check if table exists implicitly by catching error if query fails, or rely on empty list
            # Need to handle empty list for df_items['id']
            if not df_items.empty:
                ids_str = ",".join([str(x) for x in df_items['id'].tolist()])
                if ids_str:
                     results_query = f"SELECT item_pregao_id, conteudo FROM itens_resultados WHERE item_pregao_id IN ({ids_str})"
                     results_df = pd.read_sql(results_query, engine)
                     for _, r in results_df.iterrows():
                         items_with_results[r['item_pregao_id']] = r['conteudo']
        except:
            pass # Table might not exist yet

        # --- Action Buttons & Title ---
        # 6 equal columns: 1 (Back), 2-3 (Empty), 4 (PNCP), 5 (Update), 6 (Download)
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        
        if c1.button("⬅️ Voltar para a Lista", use_container_width=True):
            st.switch_page("views/3. Pregoes.py")
        
        if link_pncp:
            c4.link_button("🔗 Abrir no PNCP", link_pncp, use_container_width=True)
            
        if c5.button("🔄 Atualizar Itens", use_container_width=True):
            run_import_dialog(pregao_id)
            
        # Check if we already have results to decide the button label
        has_results = len(items_with_results) > 0
        btn_label = "🔄 Atualizar Resultados" if has_results else "📥 Baixar Resultados"
        
        if c6.button(btn_label, use_container_width=True):
            # Clean up previous state to ensure fresh run
            if f"batch_import_state_{pregao_id}" in st.session_state:
                del st.session_state[f"batch_import_state_{pregao_id}"]
            run_batch_results(pregao_id)
        
        st.title(f"📋 Itens do Pregão {pregao_ctx.get('numero')}/{pregao_ctx.get('ano')}")
        
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
        
        # Modal for Fetching Results (Removed, imported)




        
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
                c[4].write(f"R$ {v_unit:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if v_unit is not None else "-")
                
                v_total = safe_float(row.get('Valortotal') or row.get('valortotal') or row.get('valor_total'))
                c[5].write(f"R$ {v_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if v_total is not None else "-")
                
                # Action Buttons
                col_act = c[6]
                
                # Grid for buttons
                c_a1, c_a2 = col_act.columns(2)
                
                # 1. View Item Detail
                if c_a1.button("🔍", key=f"btn_item_{row_id}", help="Ver Detalhes do Item"):
                    show_item_details(row, pregao_context=pregao_ctx, result_data=items_with_results.get(row_id))
                
                st.markdown("<hr style='margin: 5px 0; opacity: 0.3;'>", unsafe_allow_html=True)
        else:
            st.info("Nenhum item encontrado para este pregão.")

except Exception as e:
    st.error(f"Erro ao carregar itens: {e}")
