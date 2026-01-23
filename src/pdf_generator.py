from fpdf import FPDF


class PregaoPDF(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 16)
        self.cell(0, 10, 'Detalhes do Pregão', border=False, new_x="LMARGIN", new_y="NEXT", align='C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}/{{nb}}', align='C')

def generate_pregao_pdf(row_data):
    pdf = PregaoPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Helper to clean data
    row_keys_norm = {k.lower(): k for k in row_data.keys()}
    
    def safe_text(text):
        if not isinstance(text, str):
            text = str(text)
        # Latin-1 Map for common chars
        replacements = {
            "–": "-",  # en dash
            "—": "-",  # em dash
            "“": '"',  # smart quotes
            "”": '"',
            "‘": "'",
            "’": "'",
            "…": "...",
            "\u2022": "*", # bullet
        }
        for k, v in replacements.items():
            text = text.replace(k, v)
            
        # Ensure compatible encoding
        return text.encode('latin-1', 'replace').decode('latin-1')

    def get_val(key_alias):
        # same logic safely reusing here or just pass processed dict?
        # Replicating logic for robustness
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
                if isinstance(raw_val, str):
                    if raw_val.lower() == "true": return "Sim"
                    if raw_val.lower() == "false": return "Não"
                if raw_val is None or raw_val == "":
                    return "-"
                return safe_text(str(raw_val))
        return "-"

    # Styles
    pdf.set_font("helvetica", "B", 12)
    
    # Section: OBJETO
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, "Objeto da Licitação", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 10)
    # MultiCell for wrapping text
    pdf.multi_cell(0, 6, get_val("objetocompra"))
    pdf.ln(5)
    
    # Section: ORGÃO
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, "Dados do Órgão", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 10)
    
    # Custom Layout for Orgão
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(40, 6, "Órgão/Entidade:", new_x="RIGHT")
    pdf.set_font("helvetica", "", 10)
    
    # Align wrapped text
    x_val = pdf.get_x()
    save_lm = pdf.l_margin
    pdf.set_left_margin(x_val)
    pdf.multi_cell(0, 6, get_val("orgaoentidade_razaosocial"))
    pdf.set_left_margin(save_lm)
    pdf.set_x(save_lm)
    
    fields_orgao = [
        ("CNPJ da Origem", "cnpj_orgao"),
        ("UASG", "unidade_orgao"),
        ("Município", "unidadeorgao_municipionome"),
        ("Estado", "unidadeorgao_ufnome"),
    ]
    
    for label, key in fields_orgao:
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(35, 6, f"{label}:", new_x="RIGHT")
        
        pdf.set_font("helvetica", "", 10)
        value = get_val(key)
        
        x_val = pdf.get_x()
        save_lm = pdf.l_margin
        pdf.set_left_margin(x_val)
        pdf.multi_cell(0, 6, value)
        pdf.set_left_margin(save_lm)
        pdf.set_x(save_lm)

    
    pdf.ln(5)

    # Section: COMPRA
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, "Dados da Compra", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 10)
    
    fields_compra = [
        ("Nº Controle PNCP", "numero_controle_pncp"),
        ("Número/Ano", ("numerocompra", "anocompra")),
        ("Sequencial PNCP", "sequencialcompra"),
        ("Modalidade", "modalidadenome"),
        ("SRP", "srp"),
        ("Data Publicação", "data_publicacao_pncp"),
        ("Nº Processo", "processo"),
        ("Data da Sessão Pública", "dataEncerramentoProposta")
    ]
    
    for label, key_ref in fields_compra:
        pdf.set_font("helvetica", "B", 10)
        
        val = ""
        if isinstance(key_ref, tuple):
             v1 = get_val(key_ref[0])
             v2 = get_val(key_ref[1])
             val = f"{v1}/{v2}"
        else:
             val = get_val(key_ref)
             
        # Print Label
        pdf.cell(35, 6, f"{label}:", new_x="RIGHT")
        
        # Print Value (Wrapped)
        pdf.set_font("helvetica", "", 10)
        
        x_val = pdf.get_x()
        save_lm = pdf.l_margin
        pdf.set_left_margin(x_val)
        pdf.multi_cell(0, 6, val)
        pdf.set_left_margin(save_lm)
        pdf.set_x(save_lm)

    pdf.ln(5)
    
    # Link
    link = get_val("linksistemaorigem")
    if link != "-":
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(40, 6, "Link Sistema:", new_x="RIGHT")
        pdf.set_font("helvetica", "U", 10)
        pdf.set_text_color(0, 0, 255)
        
        x_val = pdf.get_x()
        save_lm = pdf.l_margin
        pdf.set_left_margin(x_val)
        pdf.multi_cell(0, 6, link, link=link)
        pdf.set_left_margin(save_lm)
        pdf.set_x(save_lm)
        
        pdf.set_text_color(0, 0, 0)
    
    # Return raw bytes for st.download_button
    return bytes(pdf.output())
