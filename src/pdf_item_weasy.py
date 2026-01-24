from weasyprint import HTML, CSS
import io
import json

def generate_item_pdf_weasy(row_data, pregao_context=None, result_data=None):
    # Normalize keys
    row_keys_norm = {k.lower(): k for k in row_data.keys()}
    
    def get_val(key_alias):
        possible_keys = [key_alias.lower(), key_alias.lower().replace(" ", "_"), key_alias.lower().replace("_", "")]
        for k in possible_keys:
            if k in row_keys_norm:
                val = row_data[row_keys_norm[k]]
                if isinstance(val, bool): return "Sim" if val else "Não"
                
                # Currency check
                if "valor" in key_alias.lower():
                    try:
                        v_str = str(val).replace("R$", "").strip()
                        if "," in v_str: v_str = v_str.replace(".", "").replace(",", ".")
                        f_val = float(v_str)
                        return f"R$ {f_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    except: pass
                
                if val is None or val == "": return "-"
                return str(val)
        return "-"

    # Pregao Context HTML
    pregao_html = ""
    if pregao_context:
        pregao_html = f"""
        <h2>Origem do Item</h2>
        <table>
            <tr><th>UASG</th><td>{pregao_context.get('uasg', '-')}</td></tr>
            <tr><th>Pregão</th><td>{pregao_context.get('numero', '-')}/{pregao_context.get('ano', '-')}</td></tr>
        </table>
        """

    # Results HTML
    results_html = ""
    if result_data:
        d_res = {}
        if isinstance(result_data, str):
            try: d_res = json.loads(result_data)
            except: pass
        elif isinstance(result_data, dict):
            d_res = result_data
            
        def get_res(keys):
            for k in keys:
                if k in d_res: return d_res[k]
                if k.lower() in d_res: return d_res[k.lower()]
            return "-"
            
        # Format Results
        v_unit = get_res(["valorunitariohomologado", "valorUnitarioHomologado"])
        v_total = get_res(["valortotalhomologado", "valorTotalHomologado"])
        
        try: v_unit = f"R$ {float(v_unit):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except: pass
        try: v_total = f"R$ {float(v_total):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except: pass

        results_html = f"""
        <h2>Resultado Homologado</h2>
        <table>
            <tr><th>Fornecedor</th><td>{get_res(["nomerazaosocialfornecedor", "nomeRazaoSocialFornecedor"])}</td></tr>
            <tr><th>CNPJ/CPF</th><td>{get_res(["nifornecedor", "niFornecedor"])}</td></tr>
            <tr><th>Situação</th><td>{get_res(["situacaocompraitemresultadonome", "situacaoCompraItemResultadoNome"])}</td></tr>
            <tr><th>Data Resultado</th><td>{get_res(["dataresultado", "dataResultado"])}</td></tr>
            <tr><th>Qtd Homologada</th><td>{get_res(["quantidadehomologada", "quantidadeHomologada"])}</td></tr>
            <tr><th>Valor Unit. Estimado</th><td>{v_unit}</td></tr>
            <tr><th>Valor Total Estimado</th><td>{v_total}</td></tr>
        </table>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            @page {{ size: A4; margin: 2cm; }}
            body {{ font-family: Helvetica, Arial, sans-serif; font-size: 12px; color: #333; }}
            h1 {{ text-align: center; color: #2c3e50; border-bottom: 2px solid #2c3e50; padding-bottom: 10px; }}
            h2 {{ color: #2980b9; border-bottom: 1px solid #eee; margin-top: 20px; padding-bottom: 5px; }}
            h3 {{ margin: 0 0 10px 0; color: #555; }}
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 10px; }}
            th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #f8f9fa; color: #555; width: 35%; font-weight: bold; }}
            .box {{ background: #fdfdfd; border: 1px solid #eee; padding: 15px; margin-bottom: 20px; border-radius: 5px; }}
            .footer {{ position: fixed; bottom: 0; width: 100%; text-align: center; font-size: 10px; color: #999; }}
        </style>
    </head>
    <body>
        <h1>Detalhes do Item</h1>
        
        {pregao_html}
        
        <h2>Dados do Item</h2>
        <table>
            <tr><th>Número do Item</th><td>{get_val("numero_item")}</td></tr>
            <tr><th>Descrição</th><td>{get_val("descricao")}</td></tr>
            <tr><th>Unidade</th><td>{get_val("unidademedida")}</td></tr>
            <tr><th>Quantidade</th><td>{get_val("quantidade")}</td></tr>
            <tr><th>Material/Serviço</th><td>{get_val("materialouserviconome")}</td></tr>
            <tr><th>Situação</th><td>{get_val("situacaocompraitemnome")}</td></tr>
            <tr><th>Valor Unitário</th><td>{get_val("valor_unitario")}</td></tr>
            <tr><th>Valor Total</th><td>{get_val("valortotal")}</td></tr>
        </table>
        
        {results_html}
        
        <div class="footer">Gerado via Sistema de Inteligência de Dados - DLIH/HUPAA</div>
    </body>
    </html>
    """
    
    pdf_file = io.BytesIO()
    HTML(string=html_content).write_pdf(target=pdf_file)
    return pdf_file.getvalue()
