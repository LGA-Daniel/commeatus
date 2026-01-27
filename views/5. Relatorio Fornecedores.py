import streamlit as st
import pandas as pd
from src.database import get_db, get_engine
from src.models import Pregao, ItemPregao, ItemResultado
from sqlalchemy import text
from sqlalchemy import text
import json
from io import BytesIO
from weasyprint import HTML, CSS

st.set_page_config(page_title="Relatório por Fornecedor", page_icon="📊", layout="wide")



st.title("📊 Resultado por Fornecedor")

# 1. Fetch Available Pregoes
engine = get_engine()
pregoes_opts = {}

from datetime import datetime
import time

# --- Filters Section (Copied from Pregoes.py) ---
with st.container(border=True):
    st.subheader("Filtrar Opções de Pregão")
    
    # helper to get filter options
    @st.cache_data(ttl=60)
    def load_filter_options():
        years = [datetime.now().year]
        uasgs = []
        try:
            dates_df = pd.read_sql("SELECT DISTINCT data_publicacao_pncp FROM pregoes", engine)
            if not dates_df.empty and 'data_publicacao_pncp' in dates_df.columns:
                y = pd.to_datetime(dates_df['data_publicacao_pncp']).dt.year.unique()
                years = sorted([int(x) for x in y], reverse=True)
            
            uasg_df = pd.read_sql("SELECT DISTINCT unidade_orgao FROM pregoes", engine)
            if not uasg_df.empty and 'unidade_orgao' in uasg_df.columns:
                uasgs = sorted(uasg_df['unidade_orgao'].dropna().unique())
        except:
            pass
        return years, uasgs

    available_years, available_uasgs = load_filter_options()
    
    # Row 1: Year, UASG, Process
    c1, c2, c3 = st.columns([0.2, 0.5, 0.3])
    
    # Filter State (Local for this view)
    if "rep_years" not in st.session_state: st.session_state.rep_years = []
    if "rep_uasgs" not in st.session_state: st.session_state.rep_uasgs = []
    
    selected_years = c1.multiselect("Ano:", options=available_years, key="rep_years")
    selected_uasgs = c2.multiselect("UASG:", options=available_uasgs, key="rep_uasgs")
    search_processo = c3.text_input("Número do Processo:", placeholder="Ex: 1234/2024")
    
    # --- Build Query based on Filters ---
    pregoes_opts = {}
    try:
        # Build clauses
        where_clauses = ["1=1"]
        sql_params = {}
        
        if selected_years:
            if len(selected_years) == 1:
                where_clauses.append(f"EXTRACT(YEAR FROM data_publicacao_pncp) = {selected_years[0]}")
            else:
                where_clauses.append(f"EXTRACT(YEAR FROM data_publicacao_pncp) IN {tuple(selected_years)}")
                
        if selected_uasgs:
            clean_uasgs = [u.replace("'", "''") for u in selected_uasgs]
            in_clause = "'" + "','".join(clean_uasgs) + "'"
            where_clauses.append(f"unidade_orgao IN ({in_clause})")
        
        if search_processo:
            where_clauses.append("processo ILIKE %(proc)s")
            sql_params["proc"] = f"%{search_processo}%"

        where_str = " AND ".join(where_clauses)
        
        query_filtered = f"""
            SELECT * 
            FROM pregoes 
            WHERE {where_str}
            ORDER BY data_publicacao_pncp DESC
        """
        
        # Execute
        filtered_df = pd.read_sql(query_filtered, engine, params=sql_params)
        
        # Convert to options dict
        for _, p in filtered_df.iterrows():
             # Parse content for label
            label = f"ID {p['id']}"
            try:
                c = p['conteudo']
                # pd read_sql might give dict directly for JSON/JSONB? 
                # If standard sqlalchemy/psycopg2, it often returns dict if native json support is on, or string.
                if isinstance(c, str): c = json.loads(c)
                if isinstance(c, list) and c: c = c[0]
                
                num = c.get('numeroCompra') or c.get('numerocompra') or p['numero_controle_pncp']
                ano = c.get('anoCompra') or c.get('anocompra') or ""
                uasg = p['unidade_orgao'] or ""
                
                # Additional info for label clarity
                obj = str(c.get('objetoCompra') or c.get('objetocompra') or "")[:120]
                if len(str(c.get('objetoCompra') or c.get('objetocompra') or "")) > 120: obj += "..."
                
                label = f"{num}/{ano} | UASG: {uasg} | {obj}"
            except:
                pass
            pregoes_opts[p['id']] = label
            
    except Exception as e:
        st.error(f"Erro ao carregar e filtrar pregões: {e}")
        st.stop()

    if not pregoes_opts:
        st.warning("Nenhum pregão encontrado com os filtros atuais.")
        st.stop()

    def reset_report():
        # Clear state when selection changes
        keys_to_clear = ['active_report_id', 'export_pdf_data', 'export_csv_data']
        for k in keys_to_clear:
            if k in st.session_state:
                del st.session_state[k]

    selected_top_id = st.selectbox(
        "Selecione o Pregão para Gerar Relatório:",
        options=list(pregoes_opts.keys()),
        format_func=lambda x: pregoes_opts[x],
        on_change=reset_report,
        index=None,
        placeholder="Selecione um pregão..."
    )
    generate_btn = st.button("Gerar Relatório")

    if generate_btn and selected_top_id:
        st.session_state['active_report_id'] = selected_top_id
        # Reset export data when new report is generated
        st.session_state.export_pdf_data = None
        st.session_state.export_csv_data = None

    # Check if there is an active report ID in session state
    if 'active_report_id' in st.session_state:
        selected_top_id = st.session_state['active_report_id']
        st.divider()
    
    if selected_top_id is None:
        st.stop()

    if 'active_report_id' not in st.session_state:
        st.stop()

    # 2. Validation Logic
    # Check if any item is "Em Andamento"
    try:
        from sqlalchemy import text
        # Using text() allows safe parameter binding with SQLAlchemy
        query_val = text("""
            SELECT COUNT(*) as count
            FROM itens_pregao
            WHERE pregao_id = :pid
            AND situacaocompraitemnome ILIKE :status
        """)
        
        with engine.connect() as conn:
            items_in_progress = pd.read_sql(
                query_val,
                conn,
                params={"pid": int(selected_top_id), "status": "%Em andamento%"}
            )
    
        if items_in_progress.iloc[0]['count'] > 0:
            st.error("⚠️ Este pregão ainda possui itens com status 'Em Andamento'. O relatório só pode ser gerado após a finalização de todos os itens.")
            st.stop()
            
    except Exception as e:
        st.error(f"Erro na validação do pregão: {e}")
        st.stop()

    # 3. Data Retrieval
    # Use spinner for loading state
    with st.spinner("Gerando relatório..."):
        try:
            # Fetch Items and Results
            # Join ItemPregao and ItemResultado
            query = f"""
            SELECT 
                i.numero_item,
                i.descricao,
                r.conteudo as resultado_json
            FROM itens_pregao i
            JOIN itens_resultados r ON i.id = r.item_pregao_id
            WHERE i.pregao_id = {selected_top_id}
            ORDER BY i.numero_item ASC
            """
            
            df_results = pd.read_sql(query, engine)
            
            if df_results.empty:
                st.warning("Nenhum resultado homologado encontrado para este pregão.")
                st.stop()
    
            # Process JSON and Group
            suppliers = {} # Key: "CNPJ - Name", Value: List of items
            
            for _, row in df_results.iterrows():
                try:
                    res = row['resultado_json']
                    if isinstance(res, str): res = json.loads(res)
                    
                    # Extract Supplier Info using multiple possible keys (case insensitive safety)
                    def get_k(d, keys):
                        for k in keys:
                            if k in d: return d[k]
                            # Also try lower
                            for dk in d.keys():
                                if dk.lower() == k.lower(): return d[dk]
                        return None
    
                    cnpj = get_k(res, ['niFornecedor', 'nifornecedor']) or "Sem CNPJ"
                    name = get_k(res, ['nomeRazaoSocialFornecedor', 'nomerazaosocialfornecedor']) or "Fornecedor Desconhecido"
                    
                    supplier_key = f"{cnpj} - {name}"
                    
                    # Extract Item Data
                    qtd_homolog = get_k(res, ['quantidadeHomologada', 'quantidadehomologada']) or 0
                    val_unit = get_k(res, ['valorUnitarioHomologado', 'valorunitariohomologado']) or 0
                    val_total = get_k(res, ['valorTotalHomologado', 'valortotalhomologado']) or 0
                    
                    item_data = {
                        "Item": row['numero_item'],
                        "Descrição": row['descricao'],
                        "Qtd. Homologada": float(qtd_homolog),
                        "Valor Unit.": float(val_unit),
                        "Valor Total": float(val_total)
                    }
                    
                    if supplier_key not in suppliers:
                        suppliers[supplier_key] = {
                            "cnpj": cnpj,
                            "name": name,
                            "items": [],
                            "total_general": 0.0
                        }
                    
                    suppliers[supplier_key]["items"].append(item_data)
                    suppliers[supplier_key]["total_general"] += item_data["Valor Total"]
                    
                except Exception as px:
                    # Skip malformed lines or log?
                    continue
                    
            # 4. Visualization
            if not suppliers:
                st.warning("Dados de resultados encontrados, mas falha ao processar fornecedores.")
                st.stop()

            # --- Metrics ---
            # 1. Get Total Items for this Pregao to calculate "No Result"
            try:
                q_total = text("SELECT COUNT(*) as total FROM itens_pregao WHERE pregao_id = :pid")
                with engine.connect() as conn:
                    total_items = pd.read_sql(q_total, conn, params={"pid": int(selected_top_id)}).iloc[0]['total']
            except:
                total_items = 0
            
            items_with_result = len(df_results)
            items_no_result = total_items - items_with_result
            if items_no_result < 0: items_no_result = 0
            
            m1, m2, m3 = st.columns(3)
            
            # Helper for card style
            def card(col, label, value, border_color, bg_color):
                col.markdown(f"""
                <div style="border-left: 5px solid {border_color}; background-color: {bg_color}; padding: 15px; border-radius: 8px;">
                    <div style="font-size: 1rem; color: #FFFFFF; font-weight: 600;">{label}</div>
                    <div style="font-size: 2rem; font-weight: bold; color: {border_color};">{value}</div>
                </div>
                """, unsafe_allow_html=True)

            # Green for Results (rgba(40, 167, 69, 0.2))
            card(m1, "Itens com Resultado", items_with_result, "#28a745", "rgba(40, 167, 69, 0.3)")
            
            # Red for No Results (rgba(220, 53, 69, 0.2))
            card(m2, "Itens Sem Resultado", items_no_result, "#dc3545", "rgba(220, 53, 69, 0.3)")
            
            # Blue for Suppliers (rgba(0, 123, 255, 0.2))
            card(m3, "Número de Fornecedores", len(suppliers), "#007bff", "rgba(0, 123, 255, 0.3)")
            
            st.divider()

            # --- Helpers ---
            def fmt_currency(val):
                if pd.isna(val): return "-"
                try:
                    return f"R$ {float(val):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                except:
                    return str(val)

            def fmt_qtd(val):
                    if pd.isna(val) or val is None: return "-"
                    try: return f"{float(val):.2f}".replace(".", ",")
                    except: return str(val)

            # --- Export Logic ---
            @st.cache_data(show_spinner=False)
            def generate_csv(suppliers_data):
                all_items = []
                for key, data in suppliers_data.items():
                    for item in data['items']:
                        row = item.copy()
                        row['CNPJ Fornecedor'] = data['cnpj']
                        row['Nome Fornecedor'] = data['name']
                        all_items.append(row)
                
                if all_items:
                    df_all = pd.DataFrame(all_items)
                    # Reorder columns
                    cols = ['CNPJ Fornecedor', 'Nome Fornecedor', 'Item', 'Descrição', 'Qtd. Homologada', 'Valor Unit.', 'Valor Total']
                    # Filter only existing columns
                    cols = [c for c in cols if c in df_all.columns]
                    df_all = df_all[cols]
                    return df_all.to_csv(index=False).encode('utf-8')
                return b""

            @st.cache_data(show_spinner=False)
            def generate_pdf(suppliers_data):
                html_content = """
                <html>
                <head>
                    <style>
                        body { font-family: sans-serif; font-size: 10pt; }
                        h1 { font-size: 14pt; text-align: center; }
                        .supplier-block { margin_bottom: 20px; border: 1px solid #ccc; padding: 10px; }
                        .supplier-header { background-color: #f0f0f0; padding: 5px; font-weight: bold; }
                        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
                        th, td { border: 1px solid #ddd; padding: 4px; text-align: left; }
                        th { background-color: #eee; }
                        .text-right { text-align: right; }
                        .total-row { font-weight: bold; background-color: #e6ffe6; }
                    </style>
                </head>
                <body>
                    <h1>Relatório de Resultado por Fornecedor</h1>
                """
                
                # Sort for PDF as well
                sorted_suppliers_pdf = sorted(suppliers_data.items(), key=lambda x: x[1]['total_general'], reverse=True)
                
                for key, data in sorted_suppliers_pdf:
                    html_content += f"""
                    <div class="supplier-block">
                        <div class="supplier-header">{data['name']} (CNPJ: {data['cnpj']})</div>
                        <table>
                            <thead>
                                <tr>
                                    <th width="5%">Item</th>
                                    <th width="50%">Descrição</th>
                                    <th width="10%">Qtd.</th>
                                    <th width="15%">Unitário</th>
                                    <th width="20%">Total</th>
                                </tr>
                            </thead>
                            <tbody>
                    """
                    for item in data['items']:
                         html_content += f"""
                            <tr>
                                <td>{item['Item']}</td>
                                <td>{item['Descrição']}</td>
                                <td class="text-right">{fmt_qtd(item['Qtd. Homologada'])}</td>
                                <td class="text-right">{fmt_currency(item['Valor Unit.'])}</td>
                                <td class="text-right">{fmt_currency(item['Valor Total'])}</td>
                            </tr>
                        """
                    
                    # Total Row
                    html_content += f"""
                            <tr class="total-row">
                                <td colspan="4" class="text-right">Total do Fornecedor:</td>
                                <td class="text-right">{fmt_currency(data['total_general'])}</td>
                            </tr>
                            </tbody>
                        </table>
                    </div>
                    """
                
                html_content += "</body></html>"
                
                pdf_file = HTML(string=html_content).write_pdf()
                return pdf_file

            # Generate files only on demand
            # State management for exports
            if "export_pdf_data" not in st.session_state: st.session_state.export_pdf_data = None
            if "export_csv_data" not in st.session_state: st.session_state.export_csv_data = None
            
            # Export Buttons Layout
            c_pdf, c_csv, c_void = st.columns([1, 1, 3])
            
            # PDF Section
            with c_pdf:
                if st.session_state.export_pdf_data is None:
                    if st.button("📄 Gerar PDF", key="btn_gen_pdf"):
                        with st.spinner("Gerando PDF..."):
                            st.session_state.export_pdf_data = generate_pdf(suppliers)
                        st.rerun()
                else:
                    st.download_button(
                        label="⬇️ Baixar PDF",
                        data=st.session_state.export_pdf_data,
                        file_name="relatorio_fornecedores.pdf",
                        mime="application/pdf"
                    )
            
            # CSV Section
            with c_csv:
                if st.session_state.export_csv_data is None:
                    if st.button("📊 Gerar CSV", key="btn_gen_csv"):
                        with st.spinner("Gerando CSV..."):
                            st.session_state.export_csv_data = generate_csv(suppliers)
                        st.rerun()
                else:
                    st.download_button(
                        label="⬇️ Baixar CSV",
                        data=st.session_state.export_csv_data,
                        file_name="relatorio_fornecedores.csv",
                        mime="text/csv"
                    )

            st.divider()
            # Wrapper Expander for all results
            with st.expander("Resultados Detalhados", expanded=False):
                # Sort suppliers by total value desc
                sorted_suppliers = sorted(suppliers.items(), key=lambda x: x[1]['total_general'], reverse=True)
                
                for key, data in sorted_suppliers:
                    # Supplier Header
                    # Supplier Header (Standard Streamlit)
                    with st.container():
                        st.subheader(data['name'])
                        st.caption(f"CNPJ/CPF: {data['cnpj']}")
                    
                    # DataFrame for this supplier
                    df_sup = pd.DataFrame(data['items'])
                    
                    # Append Total Row
                    total_val = data['total_general']
                    total_row = pd.DataFrame([{
                        "Item": None,
                        "Descrição": "TOTAL FORNECEDOR",
                        "Qtd. Homologada": None,
                        "Valor Unit.": None,
                        "Valor Total": total_val
                    }])
                    df_sup = pd.concat([df_sup, total_row], ignore_index=True)
                    
                    # Format columns to Brazilian Currency Standard

        
                    # --- Visual Layout ---
                    # Header Row
                    c1, c2, c3, c4, c5 = st.columns([0.8, 4, 1.2, 1.5, 1.5])
                    c1.markdown("**Item**")
                    c2.markdown("**Descrição**")
                    c3.markdown("**Qtd.**")
                    c4.markdown("**Valor Unit.**")
                    c5.markdown("**Valor Total**")
                    
                    st.divider()
        
                    # Items Render loop
                    for item in data['items']:
                        with st.container():
                            c1, c2, c3, c4, c5 = st.columns([0.8, 4, 1.2, 1.5, 1.5])
                            
                            # Item Number (Badge style logic)
                            c1.markdown(f"**#{item['Item']}**")
                            
                            # Description
                            c2.markdown(f"{item['Descrição']}")
                            
                            # Qty
                            c3.markdown(f"{fmt_qtd(item['Qtd. Homologada'])}")
                            
                            # Values with green/bold formatting
                            v_unit = fmt_currency(item['Valor Unit.'])
                            v_total = fmt_currency(item['Valor Total'])
                            
                            c4.markdown(f"{v_unit}")
                            c5.markdown(f"**{v_total}**")
                            
                            st.markdown("<hr style='margin: 5px 0; opacity: 0.2;'>", unsafe_allow_html=True)
                    
                    # Totals Section (Standard Streamlit, Side-by-Side Label/Value)
                    t1, t2 = st.columns([2.5, 1.5])
                    with t2:
                        # Nested columns for strict separation
                        tl, tv = st.columns([1.2, 1])
                        tl.markdown("**Total do Fornecedor:**")
                        tv.markdown(f"**{fmt_currency(data['total_general'])}**")
                    
    
                    
                    st.divider()
    
        except Exception as e:
            st.error(f"Erro ao processar relatório: {e}")

