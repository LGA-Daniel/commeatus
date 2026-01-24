import requests
from src.database import get_db, engine
from src.models import Pregao, ItemPregao
from sqlalchemy.orm import Session
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def import_itens_pregao(pregao_id: int):
    """
    Fetches items for a specific Pregao from PNCP API and stores them in ItemPregao table.
    With Dynamic Schema Evolution: Checks for new columns in API data and adds them to DB.
    Returns (success: bool, message: str, count: int)
    """
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        pregao = db.query(Pregao).filter(Pregao.id == pregao_id).first()
        if not pregao:
            return False, f"Pregão ID {pregao_id} não encontrado.", 0
        
        # Extract necessary fields for API URL
        cnpj = pregao.cnpj_orgao
        
        # Try to find ano and sequencial in conteudo
        dados = pregao.conteudo
        if not dados:
             return False, "Dados do conteúdo do pregão estão vazios.", 0
             
        # 'conteudo' might be a list or string
        if isinstance(dados, list):
            if len(dados) > 0:
                dados = dados[0]
            else:
                return False, "Dados do conteúdo (lista) estão vazios.", 0
        elif isinstance(dados, str):
            import json
            try:
                parsed = json.loads(dados)
                if isinstance(parsed, list) and len(parsed) > 0:
                    dados = parsed[0]
                elif isinstance(parsed, dict):
                    dados = parsed
            except:
                pass
             
        ano_compra = dados.get('anoCompra')
        sequencial_compra = dados.get('sequencialCompra')
        
        if not ano_compra or not sequencial_compra:
             return False, f"Ano ou Sequencial não encontrados no JSON do pregão {pregao.numero_controle_pncp}.", 0

        # Build URL
        url = f"https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{ano_compra}/{sequencial_compra}/itens?pagina=1&tamanhoPagina=500"
        
        response = requests.get(url, timeout=30)
        if response.status_code != 200:
             return False, f"Erro na API PNCP: {response.status_code} - {response.text}", 0
             
        items_data = response.json()
        
        if not items_data:
            return True, "Nenhum item retornado pela API.", 0
            
        # Clear existing items for this pregao
        # Fix: Delete related results first to avoid FK violation
        from src.models import ItemResultado
        
        # 1. Get IDs of items to be deleted
        subquery = db.query(ItemPregao.id).filter(ItemPregao.pregao_id == pregao_id).subquery()
        
        # 2. Delete related results (using subquery for efficiency or direct ID list)
        # Using synchronize_session=False is important for bulk deletes that might affect session
        db.query(ItemResultado).filter(ItemResultado.item_pregao_id.in_(subquery)).delete(synchronize_session=False)
        
        # 3. Delete items
        db.query(ItemPregao).filter(ItemPregao.pregao_id == pregao_id).delete(synchronize_session=False)
        db.commit()
        
        # ---------------------------------------------------------
        # Dynamic Schema Evolution Logic
        # ---------------------------------------------------------
        
        from sqlalchemy import text, inspect
        def get_existing_columns(table_name="itens_pregao"):
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
            
        existing_columns = get_existing_columns("itens_pregao")
        count = 0
        
        for item in items_data:
            flattened_item = flatten_data(item)
            
            # Add Foreign Key
            flattened_item['pregao_id'] = pregao.id
            
            # Add full content JSON
            import json
            flattened_item['conteudo'] = json.dumps(item) 
            
            # Map specific core columns
            if 'numeroitem' in flattened_item: 
                flattened_item['numero_item'] = flattened_item['numeroitem']
                
            valor_unit = flattened_item.get('valorunitarioestimado') or flattened_item.get('valorunitariohomologado')
            if valor_unit: flattened_item['valor_unitario'] = valor_unit
            
            valor_total = flattened_item.get('valortotalestimado') or flattened_item.get('valortotalhomologado')
            if valor_total: flattened_item['valor_total'] = valor_total

            # Dynamic Column Addition
            current_keys = set(flattened_item.keys())
            new_cols = current_keys - existing_columns
            
            if new_cols:
                for col in new_cols:
                    if not col: continue
                    safe_col = "".join([c if c.isalnum() or c == '_' else '' for c in col])
                    if not safe_col: continue
                    
                    try:
                        db.execute(text(f"ALTER TABLE itens_pregao ADD COLUMN IF NOT EXISTS {safe_col} TEXT"))
                        db.commit()
                        existing_columns.add(safe_col)
                    except Exception as e:
                        print(f"Warn: Could not add column {safe_col}: {e}")
                        db.rollback()

            # Insert
            valid_data = {k: v for k, v in flattened_item.items() if k in existing_columns}
            if not valid_data: continue

            cols_str = ",".join(valid_data.keys())
            vals_str = ",".join([f":{k}" for k in valid_data.keys()])
            
            sql = text(f"INSERT INTO itens_pregao ({cols_str}) VALUES ({vals_str})")
            
            try:
                db.execute(sql, valid_data)
                count += 1
            except Exception as e:
                print(f"Insert error item {count}: {e}")
                db.rollback()
        
        db.commit()
        return True, "Itens importados com sucesso.", count
        
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc() 
        logger.error(f"Error importing items: {e}")
        return False, f"Erro interno: {str(e)}", 0
    finally:
        db.close()
