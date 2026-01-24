import streamlit as st




@st.dialog("Detalhes do Pregão", width="large")
def show_details(row_data):
    """
    Exibe os detalhes do pregão em duas seções:
    1. Dados do Órgão
    2. Dados da Compra
    """
    
    # Cleanup: Remove PDF keys from session_state that do not belong to this Item/Pregao
    current_id = str(row_data.get('id', 'x'))
    keys_to_del = []
    for k in st.session_state.keys():
        if k.startswith("pdf_") and not k.endswith(f"_{current_id}"):
            keys_to_del.append(k)
    for k in keys_to_del:
        del st.session_state[k]
    
    # PDF Print Actions
    # WeasyPrint Only
    k_pdf = f"pdf_weasy_{row_data.get('id', 'x')}"
    # Use a single column or full width since it's one button
    cont_pdf = st.empty()
    
    if k_pdf in st.session_state:
        cont_pdf.download_button(
            label="📄 Baixar PDF",
            data=st.session_state[k_pdf],
            file_name=f"pregao_weasy_{row_data.get('numerocompra', '0')}_{row_data.get('anocompra', '0')}.pdf",
            mime="application/pdf",
            type="secondary"
        )
    else:
        if cont_pdf.button("⚙️ Gerar PDF"):
            try:
                with st.spinner("Gerando PDF..."):
                    from .pdf_pregao_weasy import generate_pregao_pdf_weasy
                    pdf_bytes_w = generate_pregao_pdf_weasy(row_data)
                    st.session_state[k_pdf] = pdf_bytes_w
                    # Immediate swap
                    cont_pdf.download_button(
                        label="📄 Baixar PDF",
                        data=pdf_bytes_w,
                        file_name=f"pregao_weasy_{row_data.get('numerocompra', '0')}_{row_data.get('anocompra', '0')}.pdf",
                        mime="application/pdf",
                        type="secondary"
                    )
            except Exception as e:
                err_msg = str(e)
                if "libgobject" in err_msg or "cannot load library" in err_msg:
                    st.warning("Erro: Bibliotecas GTK3 não encontradas. WeasyPrint requer libpango/libgobject.")
                else:
                    st.warning(f"Erro ao gerar PDF: {e}")
    
    # Helper to safe get value case-insensitive
    # row_data keys might be lowercase or snake_case depending on SQL/Pandas
    # We'll normalize keys to lower() for lookup
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
                
                # Check for string "true"/"false" often returned by APIs/DBs
                if isinstance(raw_val, str):
                    if raw_val.lower() == "true": return "Sim"
                    if raw_val.lower() == "false": return "Não"
                
                # Check for Datetime/Timestamp
                if hasattr(raw_val, 'strftime'):
                    return raw_val.strftime("%d/%m/%Y")
                    
                if raw_val is None or raw_val == "":
                    return "-"
                return str(raw_val)
        return "-"

    # Section 0: OBJETO
    st.subheader("Objeto da Licitação: ")
    st.markdown(get_val("objetocompra"))
    st.divider()

    # Section 1: Dados do Órgão
    st.subheader("Dados do Órgão:")
    
    # 1.1 Órgão/Entidade (Full Width)
    st.caption("Órgão/Entidade")
    st.markdown(f"**{get_val('orgaoentidade_razaosocial')}**")
    
    # 1.2 Other Fields (2 Columns)
    fields_orgao = [
        ("CNPJ", "cnpj_orgao"),
        ("UASG", "unidade_orgao"),
        ("Município", "unidadeorgao_municipionome"),
        ("Estado", "unidadeorgao_ufnome"),
    ]

    cols_orgao = st.columns(2)
    for idx, (label, key_ref) in enumerate(fields_orgao):
        with cols_orgao[idx % 2]:
            st.caption(label)
            st.markdown(f"**{get_val(key_ref)}**")
            
    st.divider()

    # Section 2: Dados da Compra
    fields_compra = [
        ("Número de Controle PNCP", "numero_controle_pncp"),
        ("Número/Ano", ("numerocompra", "anocompra")), 
        ("Modalidade", "modalidadenome"),
        ("SRP", "srp"),
        ("Data de Publicação", "data_publicacao_pncp"),
        ("Número do Processo", "processo"), 
        ("Data da Sessão Pública", "dataEncerramentoProposta")
    ]

    st.subheader("Dados da Compra")
    cols_compra = st.columns(2)
    for idx, (label, key_ref) in enumerate(fields_compra):
        with cols_compra[idx % 2]:
            st.caption(label)
            
            # Handle Merged Fields
            if isinstance(key_ref, tuple):
                 val1 = get_val(key_ref[0])
                 val2 = get_val(key_ref[1])
                 st.markdown(f"**{val1}/{val2}**")
            elif label == "Data da Sessão Pública":
                # Special handling for date+time
                raw = get_val(key_ref)
                val_fmt = raw
                if isinstance(raw, str) and len(raw) >= 16:
                   try:
                       from datetime import datetime
                       # Clean T
                       clean_ts = raw.replace("T", " ").split(".")[0]
                       dt = datetime.fromisoformat(clean_ts)
                       val_fmt = dt.strftime("%d/%m/%Y %H:%M")
                   except:
                       pass
                st.markdown(f"**{val_fmt}**")
            else:
                 st.markdown(f"**{get_val(key_ref)}**")

    # 2.2 Link Sistema Origem (Full Width)
    link_url = get_val("linksistemaorigem")
    if link_url != "-":
        st.caption("Link do PNCP")
        st.markdown(f"[{link_url}]({link_url})")

    # Optional: Raw JSON at the bottom
    if 'conteudo' in row_data:
         with st.expander("Conteúdo JSON Bruto", expanded=False):
             st.json(row_data['conteudo'])
