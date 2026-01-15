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
