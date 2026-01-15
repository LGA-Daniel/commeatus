# Baseada em Debian, mas com o gerenciador Conda pré-instalado
FROM continuumio/miniconda3

WORKDIR /app

# 1. Criação do ambiente via Conda
# O segredo: instalamos as libs pelo canal 'conda-forge' que tem ótima compatibilidade
# e especificamos 'nomkl' para evitar otimizações da Intel que quebram CPUs antigas.
RUN conda create -n commeatus_env python=3.9 \
    streamlit \
    pandas \
    numpy \
    jupyterlab \
    psycopg2 \
    sqlalchemy \
    requests \
    aiohttp \
    schedule \
    openpyxl \
    pyjwt \
    nomkl \
    -c conda-forge -y

# 2. Configurar o shell para usar o ambiente criado por padrão
SHELL ["conda", "run", "-n", "commeatus_env", "/bin/bash", "-c"]

# Install PIP dependencies for Streamlit components (Must run inside conda env)
# unique library not present in conda-forge
RUN pip install extra-streamlit-components

# 3. Cópia do código
COPY . .

# 4. Porta e Healthcheck
EXPOSE 8501
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# 5. Execução usando o ambiente conda
ENTRYPOINT ["conda", "run", "--no-capture-output", "-n", "commeatus_env", "streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
