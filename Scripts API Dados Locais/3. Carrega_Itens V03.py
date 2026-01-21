import os
import json
import pandas as pd
import shutil
import asyncio
import aiohttp
from datetime import datetime

# --- CONFIGURAÇÕES DE ESTRUTURA PARA CORREÇÃO DO EXCEL ---
# Necessário para evitar que colunas sumam quando o dado vem null
ESTRUTURA_CATALOGO = {
    "id": None, "nome": None, "descricao": None, "dataInclusao": None, 
    "dataAtualizacao": None, "statusAtivo": None, "url": None
}
ESTRUTURA_CATEGORIA = {
    "id": None, "nome": None, "descricao": None, "dataInclusao": None, 
    "dataAtualizacao": None, "statusAtivo": None
}
ESTRUTURA_MARGEM = {
    "codigo": None, "nome": None
}

def garantir_estrutura(item):
    """
    Função auxiliar para garantir que campos nulos tenham a estrutura de dicionário,
    permitindo que o Excel gere as colunas corretamente.
    """
    if item.get('catalogo') is None:
        item['catalogo'] = ESTRUTURA_CATALOGO.copy()
    
    if item.get('categoriaItemCatalogo') is None:
        item['categoriaItemCatalogo'] = ESTRUTURA_CATEGORIA.copy()
        
    if item.get('tipoMargemPreferencia') is None:
        item['tipoMargemPreferencia'] = ESTRUTURA_MARGEM.copy()
    
    return item

def save_json(data, folder, filename):
    if isinstance(data, pd.DataFrame):
        data = data.to_dict(orient='records')
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"Arquivo JSON salvo em: {filepath}")

def save_excel(data, folder, filename): 
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)
    if os.path.exists(filepath):
        data_hora_atual = datetime.now().strftime("%Y%m%d%H%M%S")
        nome_backup = f"{os.path.splitext(filename)[0]}_bkp_{data_hora_atual}{os.path.splitext(filename)[1]}"
        caminho_backup = os.path.join(folder, nome_backup)
        shutil.copy2(filepath, caminho_backup)
        print(f"Backup criado: {caminho_backup}")

    df = pd.DataFrame(data)
    df.to_excel(filepath, index=False)
    print(f"Arquivo Excel salvo em: {filepath}")

async def fetch_with_retries(session, url, retries=100, delay=5):
    """Função para tentar fazer uma requisição com reintentos em caso de erro 429"""
    attempt = 0
    while attempt < retries:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:
                    print(f"Tentativa {attempt} = Erro 429: Limite de requisições excedido. Tentando novamente em {delay} segundos...")
                    attempt += 1
                    await asyncio.sleep(delay)
                   # delay *= 2
                else:
                    print(f"Erro {response.status} ao acessar a URL: {url}")
                    return None
        except aiohttp.ClientError as e:
            print(f"Erro ao conectar na URL {url}: {e}")
            return None
        except Exception as e:
            print(f"Erro inesperado ao acessar a URL {url}: {e}")
            return None
    print(f"Falha ao acessar {url} após {retries} tentativas.")
    return None

async def main():
    lista_compras = pd.read_excel('BASE_PNCP\\PNCP_PREGOES.xlsx')
    print("Lista de compras em BASE_PNCP\\PNCP_PREGOES.xlsx")

    # Inclui a coluna de CNPJ do órgão/entidade
    dados_uteis = lista_compras[['anoCompra', 'sequencialCompra', 'numeroControlePNCP', 'orgaoEntidade_cnpj']]
    dados_busca = list(dados_uteis.itertuples(index=False, name=None))

    print("Lista de Compras Importada com Sucesso!")
    
    # Lista temporária para processamento otimizado
    lista_itens_processados = []

    print("Iniciando Importação de Itens - API Itens PNCP")
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        tasks = []

        for anocompra, sequencialCompra, numeroControlePNCP, cnpj in dados_busca: 
            url = f"https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{anocompra}/{sequencialCompra}/itens?pagina=1&tamanhoPagina=500"
            tasks.append(fetch_with_retries(session, url))

        responses = await asyncio.gather(*tasks)

        for response, (anocompra, sequencialCompra, numeroControlePNCP, cnpj) in zip(responses, dados_busca):
            if response:
                try:
                    # Lógica de processamento corrigida, mas mantendo o bloco try/except original
                    if isinstance(response, list):
                        for item in response:
                            # Adiciona dados de controle
                            item['numeroControlePNCP'] = numeroControlePNCP
                            item['anoCompra'] = anocompra
                            item['sequencialCompra'] = sequencialCompra
                            item['orgaoEntidade_cnpj'] = cnpj
                            
                            # Aplica a correção de estrutura (campos null viram dict vazio)
                            item_estruturado = garantir_estrutura(item)
                            
                            lista_itens_processados.append(item_estruturado)
                    
                    # Nota: Não estamos mais concatenando DataFrame linha a linha para evitar lentidão
                    # e problemas de esquema, mas o try/except captura erros da mesma forma.
                except Exception as e:
                    print(f"Erro ao processar os dados para {numeroControlePNCP}: {e}")
            else:
                print(f"Falha ao obter dados para {numeroControlePNCP}. Não será processado.")

    # Criação do DataFrame final fora do loop
    if lista_itens_processados: 
        print("Busca Finalizada, exportando arquivos...")
        
        # O json_normalize com sep='_' fará o trabalho de criar as colunas expandidas
        pncp_itens = pd.json_normalize(lista_itens_processados, sep='_')

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"itens_{timestamp}.json"

        save_json(pncp_itens, "3. CARREGA ITENS\\.json", filename)
        save_excel(pncp_itens, "3. CARREGA ITENS\\.xlsx", filename.replace(".json", ".xlsx"))
        save_excel(pncp_itens, "BASE_PNCP", "PNCP_Itens.xlsx")
    else:
        print("Nenhum dado encontrado para salvar.")

asyncio.run(main())