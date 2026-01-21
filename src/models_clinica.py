from sqlalchemy import Column, Integer, Float, DateTime, String
from datetime import datetime
from .database_clinica import BaseClinica

# --- Biochemical Indicators (Monthly) ---
class IndicadorMensalBioq(BaseClinica):
    __tablename__ = 'indicadores_mensais_bioq'

    id = Column(Integer, primary_key=True, index=True)
    ano = Column(Integer, nullable=False, index=True)
    mes = Column(Integer, nullable=False, index=True) # 1 - 12
    
    # Proportions (%) - 0 to 100
    fosforo_target = Column(Float, default=0.0) # 3.5 <= P <= 5.5
    albumina_gt_3 = Column(Float, default=0.0)  # > 3.0
    pth_gt_600 = Column(Float, default=0.0)     # > 600
    
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<IndicadorMensalBioq(ano={self.ano}, mes={self.mes})>"

# --- BMI Indicators (Annual) ---
class IndicadorAnualIMC(BaseClinica):
    __tablename__ = 'indicadores_anuais_imc'

    id = Column(Integer, primary_key=True, index=True)
    ano = Column(Integer, unique=True, nullable=False, index=True)
    
    # BMI Stratification (%)
    imc_abaixo = Column(Float, default=0.0)
    imc_normal = Column(Float, default=0.0)
    imc_sobrepeso = Column(Float, default=0.0)
    imc_obesidade = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<IndicadorAnualIMC(ano={self.ano})>"
