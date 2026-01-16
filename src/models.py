from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    data_hash = Column(String, nullable=False) # Stores the hashed password
    salt = Column(String, nullable=False) # Stores the salt used for hashing
    role = Column(String, default="user") # 'admin' or 'user'
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<User(username='{self.username}', role='{self.role}')>"

from sqlalchemy.dialects.postgresql import JSONB

class Pregao(Base):
    __tablename__ = 'pregoes'

    id = Column(Integer, primary_key=True, index=True)
    numero_controle_pncp = Column(String, unique=True, index=True, nullable=False)
    data_publicacao_pncp = Column(DateTime, index=True)
    cnpj_orgao = Column(String, index=True)
    unidade_orgao = Column(String, index=True)
    conteudo = Column(JSONB) # Stores the full flattened record
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Pregao(numero='{self.numero_controle_pncp}')>"

from sqlalchemy import ForeignKey, Float
from sqlalchemy.orm import relationship

class ItemPregao(Base):
    __tablename__ = 'itens_pregao'

    id = Column(Integer, primary_key=True, index=True)
    pregao_id = Column(Integer, ForeignKey('pregoes.id'), index=True)
    
    numero_item = Column(Integer, index=True)
    descricao = Column(String)
    quantidade = Column(Float)
    valor_unitario = Column(Float, nullable=True)
    valor_total = Column(Float, nullable=True)
    
    # Store full API item object for future-proofing
    conteudo = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relation
    pregao = relationship("Pregao", backref="itens")

    def __repr__(self):
        return f"<ItemPregao(id={self.id}, item={self.numero_item})>"

class ItemResultado(Base):
    __tablename__ = 'itens_resultados'

    id = Column(Integer, primary_key=True, index=True)
    item_pregao_id = Column(Integer, ForeignKey('itens_pregao.id'), index=True)
    
    # Store full API result object
    conteudo = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relation
    item = relationship("ItemPregao", backref="resultados")

    def __repr__(self):
        return f"<ItemResultado(id={self.id}, item_id={self.item_pregao_id})>"
