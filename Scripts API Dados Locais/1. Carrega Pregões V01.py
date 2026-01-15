import os
import json
import requests
import pandas as pd
from datetime import datetime

def get_date_input(prompt):
    while True:
        try:
            date_input = input(prompt)
            datetime.strptime(date_input, "%Y%m%d")
            return date_input
        except ValueError:
            print("Data inválida. Certifique-se de usar o formato YYYYMMDD.")

def make_api_call(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao consultar a API: {e}")
        return None

def flatten_data(item):
    """Função para nivelar os dados de cada item da resposta"""
    flattened = {}

    # Para cada chave do item, verificamos se ela é um dicionário e nivelamos
    def flatten_nested(data, parent_key=""):
        if isinstance(data, dict):
            for key, value in data.items():
                new_key = f"{parent_key}{key}" if parent_key else key
                flatten_nested(value, new_key + "_")
        elif isinstance(data, list):
            for i, value in enumerate(data):
                flatten_nested(value, f"{parent_key}{i}_")
        else:
            flattened[parent_key[:-1]] = data  # Remover o último '_'

    flatten_nested(item)
    return flattened

def save_json(data, folder, filename):
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"Arquivo JSON salvo em: {filepath}")

def save_excel(data, folder, filename):
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)
    df = pd.DataFrame(data)
    df.to_excel(filepath, index=False)
    print(f"Arquivo Excel salvo em: {filepath}")

def main():
    # 1. Inputs de data (pedidos apenas uma vez)
    data_inicial = get_date_input("Digite a data inicial (YYYYMMDD): ")
    data_final = get_date_input("Digite a data final (YYYYMMDD): ")

    # 2. Definição das Listas
    cnpjs = ["15126437000143", "15126437000305"]
    
    # Adicione aqui outros códigos de unidade se necessário
    unidades_administrativas = ["155126", "155007"] 

    all_results = []

    # 3. Loop Externo (CNPJs)
    for cnpj in cnpjs:
        # 4. Loop Interno (Unidades Administrativas)
        for unidade in unidades_administrativas:
            
            page = 1
            total_pages = 1
            print(f"\n--- Iniciando consulta: CNPJ {cnpj} | Unidade {unidade} ---")

            while page <= total_pages:
                print(f"Consultando página {page}...")
                
                # Montagem da URL dinâmica com as variáveis do loop
                url = (
                    "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"
                    f"?dataInicial={data_inicial}&dataFinal={data_final}"
                    f"&codigoModalidadeContratacao=6&cnpj={cnpj}"
                    f"&codigoUnidadeAdministrativa={unidade}"
                    f"&pagina={page}&tamanhoPagina=50"
                )
                
                data = make_api_call(url)

                if not data:
                    print("Falha na consulta ou dados inválidos. Pulando para próxima etapa.")
                    break

                # Verificando se não há dados (campo "empty" ou "data" vazio)
                if data.get("empty", False) or not data.get("data"):
                    print("Nenhum dado encontrado para esta página/combinação.")
                    break

                # Nivelando e extraindo os dados
                content = data.get("data", [])     
                for item in content:
                    flattened_item = flatten_data(item)
                    all_results.append(flattened_item)

                page_info = data

                if page_info:
                    total_pages = page_info.get("totalPaginas", 1)
                    current_page = page_info.get("numeroPagina", 1)
                    if current_page > total_pages:
                        print("Número de página atual excede o total de páginas.")
                        break
                else:
                    print("Informação de páginas não encontrada na resposta. Encerrando este loop.")
                    break

                page += 1

    # 5. Salvamento final (após percorrer todos os loops)
    if all_results:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"pregoes_{timestamp}.json"

        save_json(all_results, "1. CARREGA PREGÕES\\.json", filename)
        save_excel(all_results, "1. CARREGA PREGÕES\\.xlsx", filename.replace(".json", ".xlsx"))
    else:
        print("Nenhum dado encontrado para salvar em nenhuma das consultas.")

if __name__ == "__main__":
    main()