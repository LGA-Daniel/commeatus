import os
import json
import pandas as pd
import shutil
import asyncio
import aiohttp
from datetime import datetime

def flatten_data(item):
    flattened = {}
    def flatten_nested(data, parent_key=""):
        if isinstance(data, dict):
            for key, value in data.items():
                new_key = f"{parent_key}{key}" if parent_key else key
                flatten_nested(value, new_key + "_")
        elif isinstance(data, list):
            for i, value in enumerate(data):
                flatten_nested(value, f"{parent_key}{i}_")
        else:
            flattened[parent_key[:-1]] = data
    flatten_nested(item)
    return flattened

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

async def fetch_with_retries(session, url, semaphore, retries=100, delay=1):
    async with semaphore:
        attempt = 0
        while attempt < retries:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:
                        print(f"Erro 429: Limite de requisições excedido. Tentando novamente em {delay} segundos...")
                        attempt += 1
                        await asyncio.sleep(delay)
                    elif response.status == 204:
                        return None              
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
    lista_itens = pd.read_excel('BASE_PNCP\\PNCP_Itens.xlsx')
    print("Lista de Itens em BASE_PNCP\\PNCP_Itens.xlsx")

    # Inclui o CNPJ do órgão para cada item
    dados_uteis = lista_itens[['anoCompra', 'sequencialCompra', 'numeroControlePNCP', 'numeroItem', 'orgaoEntidade_cnpj']]
    dados_busca = list(dados_uteis.itertuples(index=False, name=None))
    print("Lista de Compras Importada com Sucesso!")

    pncp_resultados = []

    print("Iniciando Importação de Resultados - API Resultados PNCP")
    timeout = aiohttp.ClientTimeout(total=30)
    semaphore = asyncio.Semaphore(6)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        tasks = []
        for anoCompra, sequencialCompra, numeroControlePNCP, numeroItem, cnpj in dados_busca:
            url = f"https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{anoCompra}/{sequencialCompra}/itens/{numeroItem}/resultados"
            tasks.append(fetch_with_retries(session, url, semaphore))

        responses = await asyncio.gather(*tasks)

        for response, (anoCompra, sequencialCompra, numeroControlePNCP, numeroItem, cnpj) in zip(responses, dados_busca):
            if response:
                try:
                    flattened_data = [flatten_data(item) for item in response]
                    for item in flattened_data:
                        item["numeroControlePNCPcompra"] = numeroControlePNCP
                        item["orgaoEntidade_cnpj"] = cnpj
                    pncp_resultados.extend(flattened_data)
                except Exception as e:
                    print(f"Erro ao processar os dados para ({numeroControlePNCP}, {numeroItem}): {e}")

    if pncp_resultados:
        print("Busca Finalizada, exportando arquivos...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"resultados_{timestamp}.json"

        df_resultados = pd.DataFrame(pncp_resultados)

        save_json(df_resultados, "4. CARREGA Resultados\\.json", filename)
        save_excel(df_resultados, "4. CARREGA Resultados\\.xlsx", filename.replace(".json", ".xlsx"))
        save_excel(df_resultados, "BASE_PNCP", "PNCP_Resultados.xlsx")
    else:
        print("Nenhum dado encontrado para salvar.")

asyncio.run(main())
