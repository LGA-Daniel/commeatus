import requests
import pandas as pd
from datetime import datetime
from sqlalchemy import text, inspect
from src.database import get_db, engine
from src.models import Pregao

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

    def flatten_nested(data, parent_key=""):
        if isinstance(data, dict):
            for key, value in data.items():
                new_key = f"{parent_key}{key}" if parent_key else key
                flatten_nested(value, new_key + "_")
        elif isinstance(data, list):
            for i, value in enumerate(data):
                flatten_nested(value, f"{parent_key}{i}_")
        else:
            # Clean keys to be SQL safe (basic)
            clean_key = parent_key[:-1]
            clean_key = clean_key.replace(".", "_").replace("-", "_").lower()
            flattened[clean_key] = data 

    flatten_nested(item)
    return flattened

def get_existing_columns(table_name="pregoes"):
    insp = inspect(engine)
    columns = [c['name'] for c in insp.get_columns(table_name)]
    return set(columns)

def run_import_pregoes(data_inicial, data_final, cnpjs=None, unidades_administrativas=None, progress_callback=None):
    if cnpjs is None:
        cnpjs = ["15126437000143", "15126437000305"]
    
    if unidades_administrativas is None:
        unidades_administrativas = ["155126", "155007"]

    db_gen = get_db()
    db = next(db_gen)
    
    total_records = 0
    errors = []
    
    # 1. Cache existing columns
    existing_columns = get_existing_columns("pregoes")
    
    try:
        for cnpj in cnpjs:
            for unidade in unidades_administrativas:
                page = 1
                total_pages = 1
                
                if progress_callback:
                    progress_callback(f"Iniciando consulta: CNPJ {cnpj} | Unidade {unidade}")

                while page <= total_pages:
                    url = (
                        "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"
                        f"?dataInicial={data_inicial}&dataFinal={data_final}"
                        f"&codigoModalidadeContratacao=6&cnpj={cnpj}"
                        f"&codigoUnidadeAdministrativa={unidade}"
                        f"&pagina={page}&tamanhoPagina=50"
                    )
                    
                    data = make_api_call(url)

                    if not data:
                        errors.append(f"Falha na consulta: CNPJ {cnpj}, Unidade {unidade}, Pag {page}")
                        break

                    if data.get("empty", False) or not data.get("data"):
                        if progress_callback:
                            progress_callback(f"Sem dados para CNPJ {cnpj}, Unidade {unidade}, Pag {page}")
                        break

                    content = data.get("data", [])     
                    new_records_count = 0
                    
                    for item in content:
                        flattened_item = flatten_data(item)
                        
                        # Add control fields
                        flattened_item['conteudo'] = pd.json_normalize(item).to_json(orient='records') # keeping json just in case
                        
                        # Fix specific fields for core columns
                        numero_controle = flattened_item.get("numerocontrolepncp")
                        if not numero_controle:
                             # Try looking in original item if flattened key mutated
                             numero_controle = item.get("numeroControlePNCP")

                        flattened_item['numero_controle_pncp'] = numero_controle
                        flattened_item['cnpj_orgao'] = cnpj
                        flattened_item['unidade_orgao'] = unidade
                        
                        data_pub = item.get("dataPublicacaoPncp")
                        if data_pub:
                             flattened_item['data_publicacao_pncp'] = data_pub

                         # remove duplicate keys that match core columns to avoid conflict if any
                        # We will use direct SQL insert, so we map flattened keys to columns
                        
                        # 2. Dynamic Schema Evolution
                        current_keys = set(flattened_item.keys())
                        new_cols = current_keys - existing_columns
                        
                        if new_cols:
                            for col in new_cols:
                                # Validation: Ensure column name is safe
                                safe_col = "".join([c if c.isalnum() or c == '_' else '' for c in col])
                                if not safe_col: continue
                                
                                try:
                                    # Add column as TEXT
                                    alter_stmt = text(f"ALTER TABLE pregoes ADD COLUMN IF NOT EXISTS {safe_col} TEXT")
                                    db.execute(alter_stmt)
                                    db.commit()
                                    existing_columns.add(safe_col)
                                except Exception as e:
                                    # Might fail if concurrent, just ignore and it might work or fail insert
                                    print(f"Warn: Could not add column {safe_col}: {e}")
                                    db.rollback()
                        
                        # 3. Upsert using raw SQL
                        # Construct columns and values
                        # Filter to only columns that exist now
                        valid_data = {k: v for k, v in flattened_item.items() if k in existing_columns}
                        
                        cols_str = ",".join(valid_data.keys())
                        # Use named parameters
                        vals_str = ",".join([f":{k}" for k in valid_data.keys()])
                        
                        updates = ", ".join([f"{k} = EXCLUDED.{k}" for k in valid_data.keys() if k != 'id'])
                        
                        sql = text(f"""
                            INSERT INTO pregoes ({cols_str}) 
                            VALUES ({vals_str})
                            ON CONFLICT (numero_controle_pncp) 
                            DO UPDATE SET {updates};
                        """)
                        
                        try:
                            db.execute(sql, valid_data)
                            new_records_count += 1
                        except Exception as e:
                            # Log but continue?
                            print(f"Insert error: {e}")
                            db.rollback() 

                    db.commit()
                    total_records += new_records_count
                    
                    if progress_callback:
                        progress_callback(f"Processado Pag {page}: {new_records_count} registros.")

                    page_info = data
                    if page_info:
                        total_pages = page_info.get("totalPaginas", 1)
                        current_page = page_info.get("numeroPagina", 1)
                        if current_page > total_pages: break
                    else:
                        break

                    page += 1
                    
    except Exception as e:
        db.rollback()
        errors.append(f"Erro crítico durante importação: {str(e)}")
        if progress_callback:
            progress_callback(f"ERRO: {str(e)}")
    finally:
        db.close()
        
    return total_records, errors
