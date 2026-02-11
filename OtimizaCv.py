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

# ---------------- CSS (VISUAL) ----------------
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #E0E0E0; }
    h1 { color: #A78BFA !important; font-family: 'Helvetica Neue', sans-serif; font-weight: 800; }
    h2, h3 { color: #F3F4F6 !important; }
    
    .hero-box {
        background: linear-gradient(90deg, #1F2937 0%, #111827 100%);
        padding: 30px;
        border-radius: 15px;
        border-left: 6px solid #8B5CF6;
        margin-bottom: 30px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    .hero-box h3 { color: #C4B5FD !important; margin-top: 0; }
    
    .stTextInput input, .stTextArea textarea { 
        background-color: #1F2937 !important; color: #FFFFFF !important; border: 1px solid #374151; border-radius: 8px;
    }
    
    [data-testid="stFileUploader"] {
        background-color: #1F2937; border: 2px dashed #6D28D9; padding: 20px; border-radius: 12px; text-align: center;
    }

    .stButton > button { 
        background: linear-gradient(90deg, #7C3AED 0%, #6D28D9 100%);
        color: white !important; width: 100%; font-size: 20px; padding: 1rem;
        border-radius: 12px; border: none; font-weight: 700; 
        box-shadow: 0 4px 14px 0 rgba(124, 58, 237, 0.39);
        transition: all 0.2s ease-in-out;
    }
    .stButton > button:hover { transform: scale(1.02); }
</style>
""", unsafe_allow_html=True)

# ---------------- HEADER ----------------
st.title("Otimizador de Currículo Express")
st.caption("Em um clique: Diagnóstico completo + Nova versão do seu CV.")

st.markdown("""
<div class="hero-box">
    <h3>Como funciona a Mágica 1-Clique:</h3>
    <p>
        Nossa IA lê seu perfil e a vaga. Em alguns segundos, ela vai:
        <br>1. 🕵️‍♀️ <b>Investigar</b> se você passa no filtro do robô recrutador.
        <br>2. ✨ <b>Reescrever</b> seu currículo automaticamente com as palavras-chave certas.
        <br>3. 🛡️ <b>Fidelidade:</b> Ela não inventará nada que não esteja no seu currículo original.
    </p>
</div>
""", unsafe_allow_html=True)

# ---------------- CONFIG ----------------
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except Exception as e:
    st.error("Erro de conexão. Verifique a chave de API nas Secrets.")
    st.stop()

# ---------------- FUNÇÕES ----------------
def extrair_texto_pdf(arquivo):
    try:
        reader = PyPDF2.PdfReader(arquivo)
        texto = ""
        for page in reader.pages:
            content = page.extract_text()
            if content:
                texto += content
        if not texto.strip():
            return "ERRO_VAZIO"
        return texto
    except:
        return "ERRO_LEITURA"

def extrair_nota_robusta(texto):
    """Extrai a nota ignorando formatações de negrito ou espaços extras."""
    match = re.search(r'(?:Nota|Minha Nota).*?(\d+)', texto, re.IGNORECASE | re.DOTALL)
    return int(match.group(1)) if match else 0

def salvar_no_sheets(email, nota, resumo_candidato, resumo_vaga, resumo_otimizacao, analise, cv_novo):
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
        gc = gspread.authorize(creds)
        sh = gc.open("Banco de Curriculos")
        sheet = sh.sheet1

        dados = [
            str(datetime.now()), 
            email, 
            f"{nota}%", 
            resumo_candidato,
            resumo_vaga,
            resumo_otimizacao,
            analise,
            cv_novo
        ]
        sheet.append_row(dados)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar na planilha: {e}")
        return False

def chamar_ia_completa(dados_cv, dados_vaga):
    # CORREÇÃO DO NOME DO MODELO: Usando a versão estável mais recente
    model = genai.GenerativeModel("gemini-flash-latest")
    
    prompt_mestre = f"""
    Atue como uma Especialista em Recolocação e ATS.
    
    REGRA DE FIDELIDADE: É proibido inventar ferramentas, cursos ou experiências que não estejam no CV original.
    
    TAREFA 1: ANÁLISE (Fale com o candidato)
    1. **Onde você brilha ✨:** (Pontos fortes)
    2. **Cuidado com isso ⚠️:** (Gaps e riscos reais. Mencione se a vaga pede algo que o candidato não tem)
    3. **Minha Nota:** X%
    4. **Veredito:** (Resumo sincero)

    TAREFA 2: OTIMIZAÇÃO (Gere o documento)
    Reescreva o currículo priorizando o que o candidato JÁ TEM e que a vaga pede.
    
    ---DIVISOR_CV---
    (Texto do Novo Currículo em Markdown)
    
    ---DIVISOR_DADOS---
    CANDIDATO: (Resumo perfil)
    VAGA: (Resumo vaga)
    MUDANCA: (O que foi priorizado)
    
    DADOS DE ENTRADA:
    CV: {dados_cv}
    VAGA: {dados_vaga}
    """
    
    resposta = model.generate_content(prompt_mestre).text
    return resposta

# ---------------- INTERFACE ----------------
col1, col2 = st.columns(2)
with col1:
    st.subheader("1. Quem é você?")
    email = st.text_input("Seu e-mail", placeholder="ex: joao@email.com")
    pdf = st.file_uploader("Seu Currículo (PDF)", type="pdf")
with col2:
    st.subheader("2. A Vaga Alvo")
    vaga = st.text_area("Descrição da Vaga", height=260, placeholder="Cole a descrição completa aqui...")

st.markdown("---")
aceite = st.checkbox("Aceito compartilhar dados para análise.")

# ---------------- BOTÃO MÁGICO ----------------
if st.button("🚀 Gerar Diagnóstico + Novo Currículo"):
    if not aceite or not email or not pdf or not vaga:
        st.warning("⚠️ Preencha tudo acima para a mágica acontecer!")
    else:
        with st.spinner("🤖 A IA está analisando seu perfil..."):
            texto_cv = extrair_texto_pdf(pdf)
            
            if texto_cv in ["ERRO_VAZIO", "ERRO_LEITURA"]:
                st.error("❌ Não conseguimos ler o texto do seu PDF. Ele pode ser uma imagem ou estar protegido.")
            else:
                try:
                    resposta_completa = chamar_ia_completa(texto_cv, vaga)
                    
                    # --- LÓGICA DE SEPARAÇÃO ROBUSTA (PLANO B) ---
                    analise = ""
                    novo_cv = ""
                    
                    if "---DIVISOR_CV---" in resposta_completa:
                        partes = resposta_completa.split("---DIVISOR_CV---")
                        analise = partes[0].strip()
                        resto = partes[1]
                        
                        if "---DIVISOR_DADOS---" in resto:
                            partes_finais = resto.split("---DIVISOR_DADOS---")
                            novo_cv = partes_finais[0].strip()
                        else:
                            novo_cv = resto.strip()
                    else:
                        # PLANO B: Se a IA falhou nos divisores, joga tudo na análise
                        analise = resposta_completa
                        novo_cv = "A IA não formatou o currículo separadamente. Verifique o texto acima."

                    # Extrai nota (usando a função robusta que te passei antes)
                 nota = extrair_nota_robusta(analise)
                    # ---------------- EXIBIÇÃO ----------------
                    st.markdown(f"## 📊 Seu Diagnóstico (Match: {nota}%)")
                    st.write(analise)
                    
                    st.markdown("---")
                    st.markdown("## ✨ Sua Nova Versão Otimizada")
                    if novo_cv:
                        st.code(novo_cv, language="markdown")
                    
                    # Salva no Sheets (opcional, se configurado)
                    salvar_no_sheets(email, nota, "Perfil Identificado", "Vaga Analisada", "Otimização Realizada", analise, novo_cv)
                    
                    st.balloons()

                except Exception as e:
                    st.error(f"Houve um erro no processamento da IA: {e}")




