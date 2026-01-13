import streamlit as st
import time

st.set_page_config(
    page_title="Commeatus",
    page_icon="📦",
    layout="centered"
)

st.write("Versão do Streamlit: " + st.__version__)
st.title("COMMEATUS")
st.caption("_Provisões. Passagem. Movimento._")
st.markdown("---")

st.subheader("Ambiente Dockerizado")
st.write("Se você vê esta mensagem, o container está rodando corretamente.")

if st.button("Ping no Servidor"):
    with st.spinner('Processando...'):
        time.sleep(1)
    st.success("✅ Pong! O sistema está vivo dentro do Docker.")
