import streamlit as st
import pandas as pd
from src.database import get_db, get_engine


# Modal for Item Details
@st.dialog("Detalhes do Item", width="large")
def show_item_details(row_data, pregao_context=None, result_data=None):
    # Cleanup: Remove PDF keys from session_state that do not belong to this Item
    current_id = str(row_data.get('id', 'x'))
    keys_to_del = []
    for k in st.session_state.keys():
        if(k.startswith("pdf_item_std_") or k.startswith("pdf_item_weasy_")) and not k.endswith(f"_{current_id}"):
            keys_to_del.append(k)
    for k in keys_to_del:
        del st.session_state[k]

    # PDF Button (WeasyPrint Only)
    k_pdf = f"pdf_item_weasy_{row_data.get('id', 'x')}"
    cont_pdf = st.empty()
    
    if k_pdf in st.session_state:
        cont_pdf.download_button(
            label="📄 Baixar PDF",
            data=st.session_state[k_pdf],
            file_name=f"item_weasy_{row_data.get('numero_item', 0)}_{pregao_context.get('numero', '') if pregao_context else ''}.pdf",
            mime="application/pdf",
            type="secondary"
        )
    else:
        if cont_pdf.button("⚙️ Gerar PDF"):
            try:
                with st.spinner("Gerando PDF..."):
                    from .pdf_item_weasy import generate_item_pdf_weasy
                    pdf_bytes_w = generate_item_pdf_weasy(row_data, pregao_context, result_data)
                    st.session_state[k_pdf] = pdf_bytes_w
                    # Immediate swap
                    cont_pdf.download_button(
                        label="📄 Baixar PDF",
                        data=pdf_bytes_w,
                        file_name=f"item_weasy_{row_data.get('numero_item', 0)}_{pregao_context.get('numero', '') if pregao_context else ''}.pdf",
                        mime="application/pdf",
                        type="secondary"
                    )
            except Exception as e:
                err_msg = str(e)
                if "libgobject" in err_msg or "cannot load library" in err_msg:
                    st.warning("Erro: Bibliotecas GTK3 não encontradas. WeasyPrint requer libpango/libgobject.")
                else:
                    st.warning(f"Erro ao gerar PDF: {e}")

    # Normalize keys for Case-Insensitive Lookup
    row_keys_norm = {k.lower(): k for k in row_data.keys()}
    
    def get_val(key_alias):
        # Allow looking up by various forms
        possible_keys = [
            key_alias.lower(),
            key_alias.lower().replace(" ", "_"),
            key_alias.lower().replace("_", "")
        ]
        
        for k in possible_keys:
            if k in row_keys_norm:
                raw_val = row_data[row_keys_norm[k]]
                if isinstance(raw_val, bool):
                    return "Sim" if raw_val else "Não"
                
                # Check for string "true"/"false"
                if isinstance(raw_val, str):
                    if raw_val.lower() == "true": return "Sim"
                    if raw_val.lower() == "false": return "Não"
                    # Try to parse ISO date string (YYYY-MM-DD...)
                    if len(raw_val) >= 10 and raw_val[4] == '-' and raw_val[7] == '-':
                        try:
                            # Quick hack for common ISO format
                            from datetime import datetime
                            # Handle T or space
                            clean_ts = raw_val.replace("T", " ")
                            # Split potential microseconds or timezone
                            clean_ts = clean_ts.split(".")[0]
                            # Try to parse, might vary
                            dt = datetime.fromisoformat(clean_ts)
                            return dt.strftime("%d/%m/%Y")
                        except:
                            pass
                
                if hasattr(raw_val, 'strftime'):
                    return raw_val.strftime("%d/%m/%Y")
                    
                if raw_val is None or raw_val == "":
                    return "-"
                return raw_val
        return "-"

    # Title & Pregao Info
    st.subheader("Origem do Item")
    # Add pregao context if available
    if pregao_context:
        c1, c2 = st.columns(2)
        c1.caption("UASG")
        c1.markdown(f"**{pregao_context.get('uasg', '-')}**")
        c2.caption("Pregão") 
        c2.markdown(f"**{pregao_context.get('numero', '-')}/{pregao_context.get('ano', '-')}**")
        st.divider()
    
    st.subheader("Detalhes Gerais")
    fields_gerais = [
        ("Item", "numero_item"),
        ("Descrição", "descricao"),
        ("Unidade de Medida", "unidademedida"),
        ("Quantidade Licitada", "quantidade"),
        ("Material/Serviço", "materialouserviconome"),
        ("Critério de Julgamento", "criteriojulgamentonome"),
        ("Situação", "situacaocompraitemnome"),
        ("Resultado", "temresultado"),
        ("Margem de Preferência", "aplicabilidademargempreferencianormal"),
        ("Última Atualização", "dataatualizacao")
    ]
    
    # 2-column grid
    cols_g = st.columns(2)
    for idx, (label, key) in enumerate(fields_gerais):
        val = get_val(key)
        # Format date if looks like date string? (Optional, kept simple string for now)
        with cols_g[idx % 2]:
            st.caption(label)
            st.markdown(str(val))
    
    fields_valores = [
        ("Valor Unitário", "valor_unitario"), # can also be 'valorunitario'
        ("Valor Total", "valortotal"),         # can also be 'valor_total'
    ]
    
    cols_v = st.columns(2)
    for idx, (label, key) in enumerate(fields_valores):
        val = get_val(key)
        # "Sigiloso" Check
        is_secret = False
        if val == "-" or val is None:
            is_secret = True
        elif isinstance(val, (int, float)) and val == 0:
            is_secret = True
        elif isinstance(val, str):
            try:
                # Clean up currency string if it came formatted from DB
                v_clean = val.replace("R$", "").replace(".", "").replace(",", ".").strip()
                if float(v_clean) == 0:
                    is_secret = True
            except:
                pass
        
        if is_secret:
            val = "Sigiloso"
        else:
            # Try to convert to float if string
            if isinstance(val, str):
                try:
                    # Clean currency symbols and spaces
                    v_clean = val.replace("R$", "").strip()
                    # Safe parsing logic:
                    # 1. If ',' exists and is the decimal separator (often last separator)
                    if "," in v_clean:
                        # Assume '.' is thousands and ',' is decimal
                        v_clean = v_clean.replace(".", "").replace(",", ".")
                    
                    val = float(v_clean)
                except:
                    pass
            
            if isinstance(val, (float, int)):
                 val = f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
             
        with cols_v[idx]:
            st.caption(label)
            st.markdown(str(val))
            
    st.divider()

    # SECTION 4: RESULTADOS
    st.subheader("Resultado")

    if result_data:
        # Show Result Data
        d_res = {}
        if isinstance(result_data, str):
            import json
            try: d_res = json.loads(result_data)
            except: d_res = {"raw": result_data}
        elif isinstance(result_data, dict):
            d_res = result_data
            
        # Define specific result fields
        fields_result = [
            ("Fornecedor", ["nomerazaosocialfornecedor", "nomeRazaoSocialFornecedor"]),
            ("CNPJ/CPF", ["nifornecedor", "niFornecedor"]),
            ("Situação", ["situacaocompraitemresultadonome", "situacaoCompraItemResultadoNome"]),
            ("Data do Resultado", ["dataresultado", "dataResultado"]),
            ("Porte do Fornecedor", ["portefornecedornome", "porteFornecedorNome"]),
            ("Qtd. Homologada", ["quantidadehomologada", "quantidadeHomologada"]),
            ("Valor Unit. Homologado", ["valorunitariohomologado", "valorUnitarioHomologado"]),
            ("Valor Total Homologado", ["valortotalhomologado", "valorTotalHomologado"]),
        ]
        
        # Helper for result values
        def get_res_val(keys):
            for k in keys:
                if k in d_res: return d_res[k]
                if k.lower() in d_res: return d_res[k.lower()]
            return "-"

        cols_r = st.columns(2)
        for idx, (label, keys) in enumerate(fields_result):
            val = get_res_val(keys)
            
            # Formatting
            if "Valor" in label and isinstance(val, (int, float)):
                 val = f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            elif "Data" in label and isinstance(val, str) and len(val) >= 10:
                 try:
                     from datetime import datetime
                     clean_ts = val.replace("T", " ").split(".")[0]
                     dt = datetime.fromisoformat(clean_ts)
                     val = dt.strftime("%d/%m/%Y")
                 except:
                     pass
            
            with cols_r[idx % 2]:
                st.caption(label)
                st.markdown(f"**{val}**")
        

            
    else:
        # Check Status for Download Button logic
        situacao = str(get_val("situacaocompraitemnome")).lower()
        if "homologado" in situacao or "adjudicado" in situacao:
             col_res_btn = st.columns([0.4, 0.6])[0]
             if col_res_btn.button("📥 Baixar Resultado", key="btn_dl_res_mod", type="primary"):
                 with st.spinner("Buscando resultado..."):
                     from src.workers.import_results import import_item_results
                     i_id = row_data.get('id')
                     if i_id:
                         ok, msg, c = import_item_results(i_id)
                         if ok:
                             st.success("Resultado baixado! Feche e abra novamente.")
                             st.rerun()
                         else: st.error(msg)
        else:
            st.info("Item sem Resultado")
            
    st.divider()
    
    # RAW JSON (Bottom)
    conteudo = row_data.get('conteudo')
    if conteudo:
        with st.expander("Conteúdo JSON Item (API)", expanded=False):
            if isinstance(conteudo, str):
                try:
                    import json
                    st.json(json.loads(conteudo))
                except:
                    st.text(conteudo)
            else:
                st.json(conteudo)

    # Result JSON (Bottom)
    if result_data:
        try:
            import json
            if isinstance(result_data, str):
                st.expander("Conteúdo JSON Resultado (API)", expanded=False).json(json.loads(result_data))
            else:
                st.expander("Conteúdo JSON Resultado (API)", expanded=False).json(result_data)
        except:
            st.expander("Conteúdo JSON Resultado (API)", expanded=False).text(result_data)


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
                display_val = str(v)
                
                # Simple heuristic for currency formatting in this dynamic view
                if "valor" in k.lower() and isinstance(v, (int, float)):
                    display_val = f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                
                with cols[idx % 2]:
                        st.text_input(k.replace("_", " ").title(), display_val, disabled=True)
                idx += 1
        
        st.divider()
        with st.expander("Conteúdo JSON Item", expanded=False):
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
        import time
        time.sleep(2)
        st.rerun()
    else:
        st.error(f"Falha: {msg}")
        if st.button("Fechar", type="primary", key="btn_close_res_dlg"):
            st.rerun()
