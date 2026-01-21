import streamlit as st
import pandas as pd
from sqlalchemy import text
from src.database_clinica import get_db_clinica, engine_clinica, BaseClinica
from src.models_clinica import IndicadorMensalBioq, IndicadorAnualIMC
import altair as alt
import datetime 

st.set_page_config(page_title="Indicadores Clínicos", page_icon="🏥", layout="wide")

st.title("🏥 Indicadores Clínicos - Diálise")

# Initialize DB (Simple migration for local sqlite)
BaseClinica.metadata.create_all(bind=engine_clinica)

tab1, tab2 = st.tabs(["📈 Dashboard", "📝 Gerenciar Dados"])

# Helper to load data
def load_bioq():
    db = next(get_db_clinica())
    try:
        data = db.query(IndicadorMensalBioq).order_by(IndicadorMensalBioq.ano, IndicadorMensalBioq.mes).all()
        return data
    finally:
        db.close()

def load_imc():
    db = next(get_db_clinica())
    try:
        data = db.query(IndicadorAnualIMC).order_by(IndicadorAnualIMC.ano).all()
        return data
    finally:
        db.close()

with tab1:
    # --- Zone 1: Combined Evolution (Line Chart) ---
    st.subheader("1. Evolução Bioquímica Geral")
    
    records_bio = load_bioq()
    if not records_bio:
        st.info("Sem dados bioquímicos para exibir.")
    else:
        # Prepare Data
        data_dicts = []
        for r in records_bio:
             dt = datetime.date(r.ano, r.mes, 1)
             data_dicts.append({
                 "Data": dt,
                 "Mês/Ano": dt.strftime("%m/%Y"),
                 "Fosforo": r.fosforo_target,
                 "Albumina": r.albumina_gt_3,
                 "PTH": r.pth_gt_600
             })
        df_bio = pd.DataFrame(data_dicts)
        
        # Melt for Line Chart
        df_melt = df_bio.melt(['Data', 'Mês/Ano'], ['Fosforo', 'Albumina', 'PTH'], var_name='Indicador', value_name='Valor (%)')
        
        # Base chart
        base_line = alt.Chart(df_melt).encode(
            x=alt.X('Data:T', axis=alt.Axis(format='%b %Y', title='Mês')),
            y=alt.Y('Valor (%)', scale=alt.Scale(domain=[0, 100])),
            color='Indicador',
            tooltip=['Mês/Ano', 'Indicador', alt.Tooltip('Valor (%)', format='.1f')]
        )
        
        line = base_line.mark_line(point=True)
        text = base_line.mark_text(align='left', dx=5, dy=-5).encode(
            text=alt.Text('Valor (%)', format='.1f')
        )
        
        st.altair_chart((line + text).interactive(), use_container_width=True)
        
        st.divider()
        
        # --- Zone 2: Individual Indicators (Bar Charts) ---
        st.subheader("2. Detalhamento por Indicador")
        
        c1, c2, c3 = st.columns(3)
        
        
        
        
        def build_mini_bar(y_col, title_text, color_val):
             # 1. Common Data & Transforms
             base = alt.Chart(df_bio).transform_joinaggregate(
                 max_val=f"max({y_col})",
                 mean_val=f"mean({y_col})"
             )
             
             # 2. X-Axis Encoding (Shared by Bar and Text)
             x_encode = alt.X('Data:T', axis=alt.Axis(format='%b %y', title=''))
             
             # 3. Bar Layer
             bar = base.mark_bar(color=color_val).encode(
                 x=x_encode,
                 y=alt.Y(y_col, scale=alt.Scale(domain=[0, 100]), title='(%)'),
                 opacity=alt.condition(
                     alt.datum[y_col] == alt.datum.max_val,
                     alt.value(1.0),
                     alt.value(0.5)
                 ),
                 tooltip=['Mês/Ano', alt.Tooltip(y_col, format='.1f', title=title_text)]
             )
             
             # 4. Text Layer
             text = base.mark_text(align='center', dy=-10, color=color_val).encode(
                 x=x_encode,
                 y=alt.Y(y_col),
                 text=alt.Text(y_col, format='.1f')
             )
             
             # 5. Rule Layer (Mean Line)
             rule = base.mark_rule(color='red', strokeDash=[4, 4], opacity=0.7).encode(
                 y=alt.Y("mean_val:Q"),
                 size=alt.value(2),
                 tooltip=[alt.Tooltip("mean_val:Q", format='.1f', title="Média")]
             )
             
             return (bar + text + rule).properties(title=title_text, height=200)

        with c1:
            st.altair_chart(build_mini_bar("Fosforo", "Fósforo (3.5 - 5.5)", "#e6550d"), use_container_width=True)
            st.caption(f":red[- - -] Média: **{df_bio['Fosforo'].mean():.1f}%**")
        with c2:
            st.altair_chart(build_mini_bar("Albumina", "Albumina > 3.0", "#3182bd"), use_container_width=True)
            st.caption(f":red[- - -] Média: **{df_bio['Albumina'].mean():.1f}%**")
        with c3:
            st.altair_chart(build_mini_bar("PTH", "PTH > 600", "#31a354"), use_container_width=True)
            st.caption(f":red[- - -] Média: **{df_bio['PTH'].mean():.1f}%**")

    st.divider()

    # --- Zone 3: BMI (Pie Chart) ---
    st.subheader("3. Estratificação de IMC")
    
    col_imc_sel, col_imc_chart = st.columns([1, 4])
    
    with col_imc_sel:
        # Load available IMC years
        records_imc = load_imc()
        if not records_imc:
            available_years = []
        else:
            available_years = sorted([r.ano for r in records_imc], reverse=True)
            
        sel_year_imc = st.selectbox("Selecione Ano", available_years if available_years else [datetime.date.today().year])

    with col_imc_chart:
        if not records_imc:
             st.info("Sem dados de IMC.")
        else:
             # Find record for selected year
             record = next((r for r in records_imc if r.ano == sel_year_imc), None)
             
             if not record:
                 st.warning(f"Sem dados para {sel_year_imc}")
             else:
                 # Data for Pie
                 pie_data = pd.DataFrame([
                     {"Categoria": "Baixo Peso", "Valor": record.imc_abaixo},
                     {"Categoria": "Eutrófico", "Valor": record.imc_normal},
                     {"Categoria": "Sobrepeso", "Valor": record.imc_sobrepeso},
                     {"Categoria": "Obesidade", "Valor": record.imc_obesidade},
                 ])
                 
                 # Color scale
                 # Order: Baixo, Normal, Sobre, Obeso
                 domain = ["Baixo Peso", "Eutrófico", "Sobrepeso", "Obesidade"]
                 range_ = ["#3182bd", "#31a354", "#e6550d", "#d62728"]
                 
                 base = alt.Chart(pie_data).encode(
                    theta=alt.Theta("Valor", stack=True)
                 )
                 
                 pie = base.mark_arc(outerRadius=120).encode(
                    color=alt.Color("Categoria", scale=alt.Scale(domain=domain, range=range_)),
                    order=alt.Order("Categoria"), # Sort order? Better use known sort or value
                    tooltip=["Categoria", alt.Tooltip("Valor", format=".1f")]
                 )
                 
                 text = base.mark_text(radius=140).encode(
                    text=alt.Text("Valor", format=".1f"),
                    order=alt.Order("Categoria"),
                    color=alt.value("black")  
                 )
                 
                 st.altair_chart(pie + text, use_container_width=True)

with tab2:
    col_form1, col_form2 = st.columns(2)
    
    # Constants
    MONTHS = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 
              7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
    REV_MONTHS = {v: k for k, v in MONTHS.items()}
    YEARS = list(range(2025, 2031))

    # --- Section: Bioquímica Mensal ---
    with col_form1:
        with st.container(border=True):
            st.subheader("Cadastro Bioquímica (Mensal)")
            
            # 1. Selection (Outside Form for interactivity)
            c_y, c_m = st.columns(2)
            sel_ano_bio = c_y.selectbox("Ano", YEARS, key="sel_bio_ano")
            sel_mes_nome = c_m.selectbox("Mês", list(MONTHS.values()), key="sel_bio_mes")
            sel_mes_num = REV_MONTHS[sel_mes_nome]
            
            # 2. Auto-load Logic
            # We use a unique key for the inputs that includes the date, OR we manage state explicitly.
            # Explicit state management is safer for 'value='.
            
            db = next(get_db_clinica())
            current_bio = None
            try:
                current_bio = db.query(IndicadorMensalBioq).filter(
                    IndicadorMensalBioq.ano == sel_ano_bio, 
                    IndicadorMensalBioq.mes == sel_mes_num
                ).first()
            finally:
                db.close()
                
            # Default values
            def_p = current_bio.fosforo_target if current_bio else 0.0
            def_alb = current_bio.albumina_gt_3 if current_bio else 0.0
            def_pth = current_bio.pth_gt_600 if current_bio else 0.0
            
            msg_status = "✏️ Editando dados existentes" if current_bio else "✨ Novo cadastro"
            st.caption(msg_status)

            # 3. Form using defaults
            with st.form("form_bioq"):
                st.markdown("**Indicadores (%)**")
                # Note: modifying value here works because the Widget Key changes if we want, 
                # BUT if we want to keep the same widget, we must ensure 'value' updates. 
                # Streamlit updates 'value' only on first render if key is static.
                # TRICK: Use key dependent on loaded data ID? No, that breaks UI flow.
                # TRICK: Use st.session_state assignment if we want to force update.
                
                # Simple approach: We don't use 'key' for the inputs, so they reset when 'value' changes? 
                # No, standard is to use keys. Let's use keys with manual state update?
                # Actually, simply keys like f"in_p_{sel_ano_bio}_{sel_mes_num}" ensures fresh widgets for new dates.
                
                k_suffix = f"{sel_ano_bio}_{sel_mes_num}"
                
                p_target = st.number_input("Prop. Fósforo (3.5 - 5.5)", 0.0, 100.0, def_p, step=0.1, key=f"p_{k_suffix}", help="Porcentagem de pacientes dentro da meta")
                alb_target = st.number_input("Prop. Albumina > 3.0", 0.0, 100.0, def_alb, step=0.1, key=f"alb_{k_suffix}")
                pth_target = st.number_input("Prop. PTH > 600", 0.0, 100.0, def_pth, step=0.1, key=f"pth_{k_suffix}")
                
                submit_bio = st.form_submit_button("Salvar Bioquímica")
                
                if submit_bio:
                    db = next(get_db_clinica())
                    try:
                        obj = db.query(IndicadorMensalBioq).filter(
                            IndicadorMensalBioq.ano == sel_ano_bio, 
                            IndicadorMensalBioq.mes == sel_mes_num
                        ).first()
                        
                        if not obj:
                            obj = IndicadorMensalBioq(ano=sel_ano_bio, mes=sel_mes_num)
                            db.add(obj)
                            msg = "Registro mensal criado!"
                        else:
                            msg = "Registro mensal atualizado!"
                        
                        obj.fosforo_target = p_target
                        obj.albumina_gt_3 = alb_target
                        obj.pth_gt_600 = pth_target
                        
                        db.commit()
                        st.success(msg)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro: {e}")
                    finally:
                        db.close()
            
            # List Bio records
            st.markdown("#### Registros Recentes")
            recs = load_bioq()
            if recs:
                 for r in reversed(recs[-5:]):
                     c1, c2 = st.columns([4,1])
                     m_name = MONTHS.get(r.mes, str(r.mes))
                     c1.caption(f"{m_name}/{r.ano} - P: {r.fosforo_target:.1f}% | Alb: {r.albumina_gt_3:.1f}%")
                     if c2.button("❌", key=f"del_bio_{r.id}"):
                         db = next(get_db_clinica())
                         db.query(IndicadorMensalBioq).filter(IndicadorMensalBioq.id == r.id).delete()
                         db.commit()
                         db.close()
                         st.rerun()

    # --- Section: IMC Anual ---
    with col_form2:
        with st.container(border=True):
            st.subheader("Cadastro IMC (Anual)")
            
            # 1. Selection
            sel_ano_imc = st.selectbox("Ano Referência", YEARS, key="sel_imc_ano")
            
            # 2. Auto-load
            db = next(get_db_clinica())
            current_imc = None
            try:
                current_imc = db.query(IndicadorAnualIMC).filter(IndicadorAnualIMC.ano == sel_ano_imc).first()
            finally:
                db.close()
            
            # Defaults
            d_imc_b = current_imc.imc_abaixo if current_imc else 0.0
            d_imc_n = current_imc.imc_normal if current_imc else 0.0
            d_imc_s = current_imc.imc_sobrepeso if current_imc else 0.0
            d_imc_o = current_imc.imc_obesidade if current_imc else 0.0
            
            msg_imc = "✏️ Editando ano existente" if current_imc else "✨ Novo ano"
            st.caption(msg_imc)

            # 3. Form
            with st.form("form_imc"):
                k_suf_imc = f"{sel_ano_imc}"
                
                st.markdown("**Distribuição (%)**")
                c_i1, c_i2 = st.columns(2)
                i_abaixo = c_i1.number_input("Baixo Peso", 0.0, 100.0, d_imc_b, step=0.1, key=f"ib_{k_suf_imc}")
                i_normal = c_i2.number_input("Eutrófico", 0.0, 100.0, d_imc_n, step=0.1, key=f"in_{k_suf_imc}")
                i_sobre = c_i1.number_input("Sobrepeso", 0.0, 100.0, d_imc_s, step=0.1, key=f"is_{k_suf_imc}")
                i_obeso = c_i2.number_input("Obesidade", 0.0, 100.0, d_imc_o, step=0.1, key=f"io_{k_suf_imc}")
                
                submit_imc = st.form_submit_button("Salvar IMC")
                
                if submit_imc:
                    db = next(get_db_clinica())
                    try:
                        obj = db.query(IndicadorAnualIMC).filter(IndicadorAnualIMC.ano == sel_ano_imc).first()
                        
                        if not obj:
                            obj = IndicadorAnualIMC(ano=sel_ano_imc)
                            db.add(obj)
                            msg = "Registro anual IMC criado!"
                        else:
                            msg = "Registro anual IMC atualizado!"
                        
                        obj.imc_abaixo = i_abaixo
                        obj.imc_normal = i_normal
                        obj.imc_sobrepeso = i_sobre
                        obj.imc_obesidade = i_obeso
                        
                        db.commit()
                        st.success(msg)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro: {e}")
                    finally:
                        db.close()

            # List IMC records
            st.markdown("#### Registros Anuais")
            recs_imc = load_imc()
            if recs_imc:
                 for r in reversed(recs_imc):
                     c1, c2 = st.columns([4,1])
                     c1.caption(f"{r.ano} - Baixo: {r.imc_abaixo:.1f}% | Normal: {r.imc_normal:.1f}%")
                     if c2.button("❌", key=f"del_imc_{r.id}"):
                         db = next(get_db_clinica())
                         db.query(IndicadorAnualIMC).filter(IndicadorAnualIMC.id == r.id).delete()
                         db.commit()
                         db.close()
                         st.rerun()
