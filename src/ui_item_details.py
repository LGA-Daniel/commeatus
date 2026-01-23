import streamlit as st
import pandas as pd
from src.database import get_db, get_engine

# Modal for Item Details
@st.dialog("Detalhes do Item", width="large")
def show_item_details(row_data, pregao_context=None, result_data=None):
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
        elif isinstance(val, (float, int)):
             val = f"R$ {val:,.2f}"
             
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
                 val = f"R$ {val:,.2f}"
            
            with cols_r[idx % 2]:
                st.caption(label)
                st.markdown(f"**{val}**")
        
        with st.expander("JSON Resultados Completo"):
            st.json(d_res)
            
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
