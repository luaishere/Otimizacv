import streamlit as st
import PyPDF2
import google.generativeai as genai
import gspread
import re
import pandas as pd
from google.oauth2.service_account import Credentials
from datetime import datetime

# ---------------- CONFIGURAÇÃO DA PÁGINA ----------------
st.set_page_config(
    page_title="Otimiza CV",
    page_icon="🎯",
    layout="wide"
)

# ---------------- CSS (UX OTIMIZADO) ----------------
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #E0E0E0; }
    .main-header { color: #A78BFA; font-size: 2.5rem; font-weight: 800; margin-bottom: 0.5rem; }
    .metric-card {
        background: #1F2937;
        padding: 20px;
        border-radius: 12px;
        border-top: 4px solid #8B5CF6;
        text-align: center;
    }
    .stButton > button { 
        background: linear-gradient(90deg, #7C3AED 0%, #6D28D9 100%);
        border: none;
        height: 3.5rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ---------------- CONFIG DE APIS ----------------
try:
    # Configuração do Gemini
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except Exception as e:
    st.error("Erro de configuração das Secrets. Verifique o painel do Streamlit.")
    st.stop()

# ---------------- FUNÇÕES DE APOIO ----------------

def extrair_texto_pdf(arquivo):
    reader = PyPDF2.PdfReader(arquivo)
    texto = ""
    for page in reader.pages:
        content = page.extract_text()
        if content: texto += content
    return texto

def extrair_nota_robusta(texto):
    match = re.search(r'(?:Nota|Minha Nota).*?(\d+)', texto, re.IGNORECASE | re.DOTALL)
    return int(match.group(1)) if match else 0

def salvar_no_sheets(email, nota, resumo_candidato, resumo_vaga, resumo_mudanca, analise, cv_novo):
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
        gc = gspread.authorize(creds)
        
        # Abre a planilha pelo nome (Certifique-se de que compartilhou com o e-mail do bot!)
        sh = gc.open("Banco de Curriculos")
        sheet = sh.sheet1

        dados = [str(datetime.now()), email, f"{nota}%", resumo_candidato, resumo_vaga, resumo_mudanca, analise, cv_novo]
        sheet.append_row(dados)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar na planilha: {e}")
        return False

def chamar_ia_agente_fiel(dados_cv, dados_vaga):
    # Alterado para 'gemini-pro' para maior compatibilidade
    model = genai.GenerativeModel("gemini-pro")
    
    prompt_mestre = f"""
    Atue como uma Especialista em Recolocação e ATS.
    
    REGRA DE OURO: PROIBIDO inventar experiências ou ferramentas que não estejam no currículo original. 

    TAREFA 1: ANÁLISE
    1. **Onde você brilha ✨**
    2. **Cuidado com isso ⚠️**
    3. **Minha Nota:** X%
    4. **Veredito**

    TAREFA 2: CURRÍCULO OTIMIZADO
    Reescreva priorizando termos da vaga que o candidato REALMENTE possui.
    
    ---DIVISOR_CV---
    (Novo CV aqui)
    
    ---DIVISOR_DADOS---
    CANDIDATO: (Resumo perfil)
    VAGA: (Resumo vaga)
    MUDANCA: (O que foi priorizado)
    
    DADOS:
    CV ORIGINAL: {dados_cv}
    VAGA ALVO: {dados_vaga}
    """
    
    resposta = model.generate_content(prompt_mestre).text
    return resposta

# ---------------- INTERFACE PRINCIPAL ----------------

st.markdown('<h1 class="main-header">CV Optimizer Pro <span style="font-size: 1rem; color: #6D28D9;">V2.1</span></h1>', unsafe_allow_html=True)

col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("📄 Seus Dados")
    email = st.text_input("E-mail para registro", placeholder="seu@email.com")
    pdf = st.file_uploader("Upload do CV Original (PDF)", type="pdf")

with col2:
    st.subheader("🎯 Vaga Alvo")
    vaga = st.text_area("Descrição da Oportunidade", height=230, placeholder="Cole aqui os requisitos da vaga...")

st.divider()
aceite = st.checkbox("Estou ciente que os dados serão processados para fins de otimização.")

if st.button("🚀 Gerar Otimização Estratégica"):
    if not (email and pdf and vaga and aceite):
        st.warning("⚠️ Preencha todos os campos corretamente.")
    else:
        with st.spinner("🤖 Agente analisando e salvando dados..."):
            try:
                texto_cv = extrair_texto_pdf(pdf)
                resposta_completa = chamar_ia_agente_fiel(texto_cv, vaga)
                
                # Parsing
                partes_cv = resposta_completa.split("---DIVISOR_CV---")
                analise = partes_cv[0].strip()
                restante = partes_cv[1] if len(partes_cv) > 1 else ""
                
                partes_dados = restante.split("---DIVISOR_DADOS---")
                novo_cv = partes_dados[0].strip()
                
                # Extração de metadados para o Sheets
                bloco_dados = partes_dados[1] if len(partes_dados) > 1 else ""
                res_c, res_v, res_m = "N/A", "N/A", "N/A"
                for linha in bloco_dados.split('\n'):
                    if "CANDIDATO:" in linha: res_c = linha.replace("CANDIDATO:", "").strip()
                    if "VAGA:" in linha: res_v = linha.replace("VAGA:", "").strip()
                    if "MUDANCA:" in linha: res_m = linha.replace("MUDANCA:", "").strip()

                nota = extrair_nota_robusta(analise)

                # Salvar no Google Sheets
                salvar_no_sheets(email, nota, res_c, res_v, res_m, analise, novo_cv)

                # Exibição
                aba1, aba2 = st.tabs(["📊 Diagnóstico", "✨ Novo Currículo"])
                with aba1:
                    st.markdown(f"### Score de Match: {nota}%")
                    st.markdown(analise)
                with aba2:
                    st.text_area("Copie seu novo currículo:", value=novo_cv, height=400)
                    st.download_button("Baixar TXT", novo_cv, file_name="cv_otimizado.txt")
                
                st.balloons()

            except Exception as e:
                st.error(f"Erro técnico: {e}")
