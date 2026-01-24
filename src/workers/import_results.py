import requests
from src.database import get_db, engine
from src.models import Pregao, ItemPregao, ItemResultado
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect
import logging
import json

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_existing_columns(table_name="itens_resultados"):
    insp = inspect(engine)
    columns = [c['name'] for c in insp.get_columns(table_name)]
    return set(columns)

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
            clean_key = parent_key[:-1] if parent_key.endswith("_") else parent_key
            if not clean_key and not isinstance(data, (dict, list)):
                 clean_key = "value"
                 
            # Clean keys
            clean_key = clean_key.replace(".", "_").replace("-", "_").lower()
            flattened[clean_key] = data 
    flatten_nested(item)
    return flattened

def import_item_results(item_pregao_id: int):
    """
    Fetches results for a specific Item and stores them in ItemResultado table.
    With Dynamic Schema Evolution.
    Returns (success: bool, message: str, count: int)
    """
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        # Get Item and Parent Pregao
        item_obj = db.query(ItemPregao).filter(ItemPregao.id == item_pregao_id).first()
        if not item_obj:
            return False, f"Item ID {item_pregao_id} não encontrado.", 0
            
        pregao = item_obj.pregao
        if not pregao:
            return False, "Pregão vinculado não encontrado.", 0
            
        # Extract params
        cnpj = pregao.cnpj_orgao
        numero_item = item_obj.numero_item
        
        # Parse Pregao content to get ano/sequencial
        dados_pregao = pregao.conteudo
        # Handle various storage formats (list, str, dict)
        if isinstance(dados_pregao, str):
            try: dados_pregao = json.loads(dados_pregao)
            except: pass
        if isinstance(dados_pregao, list) and dados_pregao:
            dados_pregao = dados_pregao[0]
            
        if not isinstance(dados_pregao, dict):
             return False, "Erro ao ler dados do pregão (conteudo inválido).", 0
             
        ano_compra = dados_pregao.get('anoCompra')
        sequencial_compra = dados_pregao.get('sequencialCompra')
        
        if not ano_compra or not sequencial_compra:
             return False, "Ano ou Sequencial de compra não encontrados.", 0

        # API Call
        url = f"https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{ano_compra}/{sequencial_compra}/itens/{numero_item}/resultados"
        
        response = requests.get(url, timeout=30)
        
        if response.status_code == 204: # No Content (common for no results yet)
             return True, "Nenhum resultado disponível para este item (204).", 0
             
        if response.status_code != 200:
             return False, f"Erro na API PNCP: {response.status_code} - {response.text}", 0
             
        results_data = response.json()
        if not results_data:
             return True, "API retornou lista vazia de resultados.", 0
             
        # Clear existing results for this item
        # Do not commit yet to ensure atomicity if inserts fail
        db.query(ItemResultado).filter(ItemResultado.item_pregao_id == item_pregao_id).delete()
        # db.commit() <- Removed to allow rollback of delete if fetch/insert fails
        
        # Dynamic Schema Logic
        existing_columns = get_existing_columns("itens_resultados")
        count = 0
        
        for res in results_data:
            flattened_res = flatten_data(res)
            
            # Add FK and Content
            flattened_res['item_pregao_id'] = item_obj.id
            flattened_res['conteudo'] = json.dumps(res)
            
            # Dynamic Column Addition
            current_keys = set(flattened_res.keys())
            new_cols = current_keys - existing_columns
            
            if new_cols:
                for col in new_cols:
                    if not col: continue
                    safe_col = "".join([c if c.isalnum() or c == '_' else '' for c in col])
                    if not safe_col: continue
                    
                    try:
                        # Default to TEXT for flexibility
                        db.execute(text(f"ALTER TABLE itens_resultados ADD COLUMN IF NOT EXISTS {safe_col} TEXT"))
                        db.commit()
                        existing_columns.add(safe_col)
                    except Exception as e:
                        logger.warning(f"Could not add column {safe_col}: {e}")
                        db.rollback()

            # Insert
            valid_data = {k: v for k, v in flattened_res.items() if k in existing_columns}
            if not valid_data: continue

            cols_str = ",".join(valid_data.keys())
            vals_str = ",".join([f":{k}" for k in valid_data.keys()])
            
            sql = text(f"INSERT INTO itens_resultados ({cols_str}) VALUES ({vals_str})")
            
            try:
                db.execute(sql, valid_data)
                count += 1
            except Exception as e:
                # If an insert fails, we must fail the whole operation to preserve atomicity/state
                logger.error(f"Insert error result {count}: {e}")
                raise e # Trigger outer rollback
        
        if results_data and count == 0:
             # We had data but inserted nothing? Rollback delete
             raise Exception("API returned data but no records were inserted (parsing error?).")

        db.commit()
        return True, "Resultados importados com sucesso.", count

    except Exception as e:
        db.rollback()
        logger.error(f"Erro critical import_item_results: {e}")
        return False, f"Erro: {str(e)}", 0
    finally:
        db.close()
