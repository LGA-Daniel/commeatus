import streamlit as st
import time
import sys

st.set_page_config(
    page_title="SID-DLIH",
    page_icon="📦",
    layout="centered"
)


st.title("SID-DLIH")
st.subheader("Sistema de Inteligência de Dados de Infraestrutura e Logística Hospitalar")
st.markdown("---")

st.caption("Versão: Alfa 1")
st.caption("Streamlit " + st.__version__)

st.caption("Python " + sys.version)
st.caption("Desenvolvido por: DLIH/HUPAA-UFAL")


footer = f"""
<style>
    .footer {{
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: transparent;
        color: grey;
        text-align: center;
        padding: 10px;
        font-size: 12px;
    }}
</style>
<div class="footer">
    <p style="margin-bottom: 0px;">Versão: Alfa 1 | Streamlit {st.__version__} | Python {sys.version.split()[0]}</p>
    <p style="margin-bottom: 0px;">Desenvolvido por: DLIH/HUPAA-UFAL</p>
</div>
"""
st.markdown(footer, unsafe_allow_html=True)