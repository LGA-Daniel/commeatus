import streamlit as st
import time

# 1. Configuração da Página (Deve ser sempre o primeiro comando Streamlit)
st.set_page_config(
    page_title="Commeatus",
    page_icon="📦",  # Ícone alusivo a suprimentos/transporte
    layout="centered", # Layout centralizado para estilo Landing Page
    initial_sidebar_state="collapsed"
)

# 2. Cabeçalho e Título
st.title("COMMEATUS")
st.caption("_Suprimentos. Provisões._")

st.markdown("---")

# 3. Área de Boas-vindas
st.subheader("Bem-vindo ao Ambiente de Desenvolvimento")
st.write(
    """
    Este é o ponto de partida do projeto **Commeatus**. 
    Se você está lendo isso, o servidor Streamlit está rodando corretamente.
    """
)

# 4. Teste de Interatividade (Validação de Estado)
# Adicionamos um botão simples para garantir que o backend está respondendo
if st.button("Verificar Status do Servidor"):
    with st.spinner('Verificando integridade...'):
        time.sleep(1.5) # Simulação de processamento
    st.success("✅ Servidor Operacional e pronto para o desenvolvimento.")
    
# 5. Rodapé Técnico (Opcional, bom para dev)
st.markdown("---")
st.markdown(
    "<small>Ambiente: Python | Framework: Streamlit v" + st.__version__ + "</small>", 
    unsafe_allow_html=True
)
