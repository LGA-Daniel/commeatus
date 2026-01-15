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
                years = sorted(y, reverse=True)
            
            # Get UASGs
            uasg_df = pd.read_sql("SELECT DISTINCT unidade_orgao FROM pregoes", engine)
            if not uasg_df.empty and 'unidade_orgao' in uasg_df.columns:
                uasgs = sorted(uasg_df['unidade_orgao'].dropna().unique())
        except:
            pass
        return years, uasgs

    engine = get_engine()
    available_years, available_uasgs = load_filter_options()
    
    # Initialize session state
    if "filter_years" not in st.session_state: st.session_state.filter_years = available_years[:1]
    if "filter_uasgs" not in st.session_state: st.session_state.filter_uasgs = []
    if "filter_search" not in st.session_state: st.session_state.filter_search = ""

    selected_years = c1.multiselect("Anos", options=available_years, default=st.session_state.filter_years, key="filter_years")
    selected_uasgs = c2.multiselect("UASG / Unidade", options=available_uasgs, default=st.session_state.filter_uasgs, key="filter_uasgs")
    
    # Row 2: Search
    search_query = st.text_input("Busca Livre", placeholder="Ex: Computadores, 12345/2023...", key="filter_search")

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
            with cols[idx % 2]:
                with st.container(border=True):
                    st.caption(display_key)
                    st.markdown(val_str)
            idx += 1
            
    # Also show raw JSON content if available
    if 'conteudo' in row_data:
         with st.expander("Conteúdo JSON Bruto"):
             st.json(row_data['conteudo'])

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
        where_clauses.append("conteudo::text ILIKE %(search)s")
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
                    
                    # 5. Botão Detalhe
                    if c[4].button("🔍", key=f"btn_{row['id']}", help="Ver Detalhes"):
                        show_details(row)
                        
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
