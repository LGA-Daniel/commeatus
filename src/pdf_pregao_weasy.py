from weasyprint import HTML, CSS
import io

def generate_pregao_pdf_weasy(row_data):
    # Normalize keys
    row_keys_norm = {k.lower(): k for k in row_data.keys()}
    
    def get_val(key_alias):
        possible_keys = [key_alias.lower(), key_alias.lower().replace(" ", "_"), key_alias.lower().replace("_", "")]
        for k in possible_keys:
            if k in row_keys_norm:
                val = row_data[row_keys_norm[k]]
                if isinstance(val, bool): return "Sim" if val else "Não"
                if val is None or val == "": return "-"
                return str(val)
        return "-"

    # HTML Content Construction
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            @page {{ size: A4; margin: 2cm; }}
            body {{ font-family: Helvetica, Arial, sans-serif; font-size: 12px; color: #333; }}
            h1 {{ text-align: center; color: #2c3e50; border-bottom: 2px solid #2c3e50; padding-bottom: 10px; }}
            h2 {{ color: #2980b9; border-bottom: 1px solid #eee; margin-top: 20px; padding-bottom: 5px; }}
            .section {{ margin-bottom: 15px; }}
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 10px; }}
            th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #f8f9fa; color: #555; width: 30%; font-weight: bold; }}
            .full-width {{ width: 100%; background: #f0f4f8; padding: 10px; border-radius: 4px; border: 1px solid #dce4ec; }}
            .footer {{ position: fixed; bottom: 0; width: 100%; text-align: center; font-size: 10px; color: #999; }}
        </style>
    </head>
    <body>
        <h1>Detalhes do Pregão</h1>
        
        <h2>Objeto</h2>
        <div class="full-width">
            {get_val("objetocompra")}
        </div>

        <h2>Dados do Órgão</h2>
        <table>
            <tr><th>Órgão/Entidade</th><td>{get_val("orgaoentidade_razaosocial")}</td></tr>
            <tr><th>CNPJ da Origem</th><td>{get_val("cnpj_orgao")}</td></tr>
            <tr><th>UASG</th><td>{get_val("unidade_orgao")}</td></tr>
            <tr><th>Município/UF</th><td>{get_val("unidadeorgao_municipionome")} / {get_val("unidadeorgao_ufnome")}</td></tr>
        </table>

        <h2>Dados da Compra</h2>
        <table>
            <tr><th>Nº Controle PNCP</th><td>{get_val("numero_controle_pncp")}</td></tr>
            <tr><th>Número/Ano</th><td>{get_val("numerocompra")}/{get_val("anocompra")}</td></tr>
            <tr><th>Modalidade</th><td>{get_val("modalidadenome")}</td></tr>
            <tr><th>SRP</th><td>{get_val("srp")}</td></tr>
            <tr><th>Data Publicação</th><td>{get_val("data_publicacao_pncp")}</td></tr>
            <tr><th>Nº Processo</th><td>{get_val("processo")}</td></tr>
            <tr><th>Data da Sessão Pública</th><td>{get_val("dataEncerramentoProposta")}</td></tr>
        </table>
        
        <br>
        <p><strong>Link do Sistema:</strong> <a href="{get_val("linksistemaorigem")}">{get_val("linksistemaorigem")}</a></p>
        
        <div class="footer">Gerado via WeasyPrint</div>
    </body>
    </html>
    """
    
    # Generate PDF
    pdf_file = io.BytesIO()
    HTML(string=html_content).write_pdf(target=pdf_file)
    return pdf_file.getvalue()
