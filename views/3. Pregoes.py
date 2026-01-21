import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from src.database import get_engine

st.set_page_config(page_title="Dashboard Pregões", page_icon="📊", layout="wide")

st.title("📊 Painel de Pregões (PNCP)")

# --- CSS for Custom Table ---
st.markdown("""
<style>
    .stButton button {
        width: 100%;
    }
    .row-header {
        font_weight: bold;
        border-bottom: 2px solid #f0f2f6;
        padding-bottom: 10px;
        margin-bottom: 10px;
    }
    .row-item {
        padding: 10px 0;
        border-bottom: 1px solid #f0f2f6;
        align-items: center;
    }
    div[role="dialog"][aria-modal="true"] {
        max-width: 60vw !important;
        width: 60vw !important;
    }
</style>
""", unsafe_allow_html=True)

# Filters
# Filters
with st.container(border=True):
    st.subheader("Filtros de Pesquisa")
    
    # Row 1: Year & UASG
    c1, c2 = st.columns([1, 2])
    
    # helper to get filter options
    @st.cache_data(ttl=60)
    def load_filter_options():
        years = [datetime.now().year]
        uasgs = []
        try:
            # Get Years
            dates_df = pd.read_sql("SELECT DISTINCT data_publicacao_pncp FROM pregoes", engine)
            if not dates_df.empty and 'data_publicacao_pncp' in dates_df.columns:
                y = pd.to_datetime(dates_df['data_publicacao_pncp']).dt.year.unique()
                years = sorted([int(x) for x in y], reverse=True)
            
            # Get UASGs
            uasg_df = pd.read_sql("SELECT DISTINCT unidade_orgao FROM pregoes", engine)
            if not uasg_df.empty and 'unidade_orgao' in uasg_df.columns:
                uasgs = sorted(uasg_df['unidade_orgao'].dropna().unique())
        except:
            pass
        return years, uasgs

    engine = get_engine()
    available_years, available_uasgs = load_filter_options()
    
    # Initialize persistent session state
    if "p_filter_years" not in st.session_state: st.session_state.p_filter_years = []
    if "p_filter_uasgs" not in st.session_state: st.session_state.p_filter_uasgs = []
    if "p_filter_search" not in st.session_state: st.session_state.p_filter_search = ""

    # Widgets use 'value' from persistent state
    # We don't use 'key' to bind directly because the widget would be cleared on page switch
    selected_years = c1.multiselect("Anos", options=available_years, default=st.session_state.p_filter_years)
    selected_uasgs = c2.multiselect("UASG / Unidade", options=available_uasgs, default=st.session_state.p_filter_uasgs)
    
    # Row 2: Search
    search_query = st.text_input("Busca Livre", value=st.session_state.p_filter_search, placeholder="Ex: Computadores, 12345/2023...")
    
    # Update persistent state immediately
    st.session_state.p_filter_years = selected_years
    st.session_state.p_filter_uasgs = selected_uasgs
    st.session_state.p_filter_search = search_query

# Modal for Worker Results
@st.dialog("Resultado da Operação")
def show_worker_result(success, msg, count):
    if success:
        st.success(f"{msg}")
        if count > 0:
            st.info(f"Registros processados: {count}")
    else:
        st.error(f"Erro: {msg}")

# Check for pending worker results
if "worker_result" in st.session_state:
    res = st.session_state.worker_result
    show_worker_result(res['success'], res['msg'], res['count'])
    del st.session_state.worker_result

# Modal for Details
@st.dialog("Detalhes do Pregão", width="large")
def show_details(row_data):
    # Display all fields
    # Clean up internal keys if needed
    exclude = ['conteudo', 'created_at'] # optionally exclude technical fields
    
    st.subheader(f"Pregão: {row_data.get('numero_controle_pncp', 'N/A')}")
    
    col1, col2 = st.columns(2)
    cols = [col1, col2]
    
    idx = 0
    for key, value in row_data.items():
        if key not in exclude:
            # Format key for display
            display_key = key.replace("_", " ").title()
            val_str = str(value)
            
            # Alternate columns
    # Alternate columns
            with cols[idx % 2]:
                with st.container(border=True):
                    st.caption(display_key)
                    st.markdown(val_str)
            idx += 1
            
    # Also show raw JSON content if available
    if 'conteudo' in row_data:
         with st.expander("Conteúdo JSON Bruto"):
             st.json(row_data['conteudo'])

# Modal for Execution with Feedback
@st.dialog("Sincronização de Itens")
def run_import_dialog(pregao_id):
    st.write("Conectando à API PNCP...")
    
    # Create a container for status updates
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

# Load Data
if True:
    # engine is already defined above
    
    # Base params
    sql_params = {}
    
    # Dynamic WHERE clause
    where_clauses = ["1=1"] # Default true
    
    if selected_years:
        if len(selected_years) == 1:
            where_clauses.append(f"EXTRACT(YEAR FROM data_publicacao_pncp) = {selected_years[0]}")
        else:
            where_clauses.append(f"EXTRACT(YEAR FROM data_publicacao_pncp) IN {tuple(selected_years)}")
            
    if selected_uasgs:
        if len(selected_uasgs) == 1:
            where_clauses.append("unidade_orgao = %(uasg)s")
            sql_params['uasg'] = selected_uasgs[0]
        else:
            # Using tuple directly in f-string is risky with text/sqla but multiselect strings are usually safe if handled carefully. 
            # Better to safe bind, but for dynamic IN clause with psycopg2 logic, simple tuple string injection often works if values are clean.
            # UASG names might have quotes/chars. safer approach used below
            clean_uasgs = [u.replace("'", "''") for u in selected_uasgs]
            in_clause = "'" + "','".join(clean_uasgs) + "'"
            where_clauses.append(f"unidade_orgao IN ({in_clause})")
    
    if search_query:
        # Search in the full JSON content cast to text for broad coverage
        # Also explicitly check for "Number/Year" format which isn't contiguous in JSON
        clause = """(
            conteudo::text ILIKE %(search)s
            OR CONCAT(conteudo->>'numeroCompra', '/', conteudo->>'anoCompra') ILIKE %(search)s
            OR CONCAT(conteudo->>'sequencialCompra', '/', conteudo->>'anoCompra') ILIKE %(search)s
        )"""
        where_clauses.append(clause)
        sql_params["search"] = f"%{search_query}%"
        
    where_str = " AND ".join(where_clauses)
    
    query = f"""
        SELECT * 
        FROM pregoes 
        WHERE {where_str}
        ORDER BY data_publicacao_pncp DESC
    """
    
    try:
        df = pd.read_sql(
            query, 
            engine, 
            params=sql_params
        )
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Encontrado", len(df))
        
        if not df.empty:
            st.divider()
            
            # Pagination
            rows_per_page = 20
            if "page" not in st.session_state: st.session_state.page = 0
            
            total_pages = max(1, (len(df) - 1) // rows_per_page + 1)
            
            # Header
            cols = st.columns([2, 2, 2, 4, 1])
            headers = ["Modalidade", "Unidade", "Compra/Ano", "Objeto", "Ação"]
            
            # Helper to safely get col value
            def get_val(row, default_col, fallback=None):
                # Try finding exact match or lowercase match
                if default_col in row: return row[default_col]
                lower_map = {k.lower(): k for k in row.keys()}
                if default_col.lower() in lower_map: return row[lower_map[default_col.lower()]]
                return fallback or "-"

            # Render Header
            st.markdown('<div class="row-header">', unsafe_allow_html=True)
            for col, h in zip(cols, headers):
                col.markdown(f"**{h}**")
            st.markdown('</div>', unsafe_allow_html=True)

            # Render Rows
            start_idx = st.session_state.page * rows_per_page
            end_idx = start_idx + rows_per_page
            
            paginated_df = df.iloc[start_idx:end_idx]
            
            # Optimization: Fetch IDs that have items
            pregoes_with_items = set()
            try:
                # Check directly in the items table
                items_df = pd.read_sql(
                    f"SELECT DISTINCT pregao_id FROM itens_pregao WHERE pregao_id IN {tuple(paginated_df['id'].tolist()) + (0,)}", 
                    engine
                )
                pregoes_with_items = set(items_df['pregao_id'].tolist())
            except Exception:
                # Table might not exist yet
                pass
            
            for idx, row in paginated_df.iterrows():
                with st.container():
                    c = st.columns([2, 2, 2, 4, 1])
                    
                    # 1. Modalidade
                    c[0].write(get_val(row, 'modalidadenome'))
                    # 2. Unidade
                    c[1].write(get_val(row, 'unidade_orgao')) # or unidadeorgao_nomeunidade
                    # 3. Compra/Ano
                    num = get_val(row, 'numerocompra')
                    ano = get_val(row, 'anocompra')
                    c[2].write(f"{num}/{ano}")
                    # 4. Objeto
                    objeto = str(get_val(row, 'objetocompra'))
                    # Removed truncation to allow standard wrapping
                    c[3].write(objeto)
                    
                    # 5. Ações (Itens)
                    col_act1, col_act2 = c[4].columns(2)
                    
                    # Button 1: Modal Details (Original)
                    if col_act1.button("🔍", key=f"btn_modal_{row['id']}", help="Ver Dados do Pregão"):
                        show_details(row)

                    # Button 2: Items Logic
                    # Check if this pregao has items loaded
                    has_items = row['id'] in pregoes_with_items
                    
                    if has_items:
                        if col_act2.button("📋", key=f"btn_det_{row['id']}", help="Ver Itens"):
                            st.session_state['selected_pregao_id'] = int(row['id'])
                            st.switch_page("views/4. Detalhes Itens.py")
                    else:
                        if col_act2.button("📥", key=f"btn_load_{row['id']}", help="Carregar Itens da API"):
                            run_import_dialog(int(row['id']))
                        
                    st.markdown("---")
            
            # Pagination Controls
            c1, c2, c3 = st.columns([1, 8, 1])
            if c1.button("Anterior") and st.session_state.page > 0:
                st.session_state.page -= 1
                st.rerun()
            
            c2.markdown(f"<div style='text-align: center'>Página {st.session_state.page + 1} de {total_pages}</div>", unsafe_allow_html=True)
            
            if c3.button("Próxima") and st.session_state.page < total_pages - 1:
                st.session_state.page += 1
                st.rerun()
                
        else:
            st.info("Nenhum dado encontrado.")
            
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
