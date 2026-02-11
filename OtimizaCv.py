import streamlit as st
import PyPDF2
import google.generativeai as genai
import gspread
import re
from google.oauth2.service_account import Credentials
from datetime import datetime

# ---------------- CONFIGURAÇÃO DA PÁGINA ----------------
st.set_page_config(
    page_title="Otimiza CV",
    page_icon="🎯",
    layout="wide"
)

# ---------------- CSS (VISUAL LIMPO E PRÁTICO) ----------------
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #E0E0E0; }
    h1 { color: #A78BFA !important; font-weight: 800; }
    .hero-box {
        background: linear-gradient(90deg, #1F2937 0%, #111827 100%);
        padding: 25px;
        border-radius: 12px;
        border-left: 5px solid #8B5CF6;
        margin-bottom: 25px;
    }
    .stButton > button { 
        background: linear-gradient(90deg, #7C3AED 0%, #6D28D9 100%);
        color: white !important; font-weight: 700; border-radius: 10px; border: none; width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# ---------------- CONFIGURAÇÃO IA ----------------
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except:
    st.error("Erro de conexão. Verifique as Secrets no Streamlit.")
    st.stop()

# ---------------- FUNÇÕES DE SUPORTE ----------------
def extrair_texto_pdf(arquivo):
    try:
        reader = PyPDF2.PdfReader(arquivo)
        texto = ""
        for page in reader.pages:
            content = page.extract_text()
            if content: texto += content
        return texto.strip() if texto else "ERRO_VAZIO"
    except:
        return "ERRO_LEITURA"

def limpar_markdown_resumo(texto):
    """Remove sujeira de markdown para exibição limpa em cards."""
    if not texto: return "N/A"
    return texto.replace("**", "").replace("#", "").strip()

def extrair_nota_robusta(texto):
    match = re.search(r'(?:Nota|Minha Nota).*?(\d+)', texto, re.IGNORECASE | re.DOTALL)
    return int(match.group(1)) if match else 0

def salvar_no_sheets(email, nota, res_cand, res_vaga, res_mud, analise, cv_novo):
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
        gc = gspread.authorize(creds)
        sh = gc.open("Banco de Curriculos")
        sheet = sh.sheet1
        dados = [str(datetime.now()), email, f"{nota}%", res_cand, res_vaga, res_mud, analise, cv_novo]
        sheet.append_row(dados)
    except Exception as e:
        st.error(f"Erro ao salvar no banco: {e}")

def chamar_ia(dados_cv, dados_vaga):
    model = genai.GenerativeModel("gemini-flash-latest")
    prompt = f"""
    Atue como Especialista em ATS. REGRA: NÃO invente informações.
    
    TAREFA 1: ANÁLISE
    1. **Onde você brilha ✨**
    2. **Cuidado com isso ⚠️**
    3. **Minha Nota:** X%
    4. **Veredito**

    TAREFA 2: OTIMIZAÇÃO
    Reescreva o currículo focado na vaga usando APENAS dados reais do CV original.
    
    ---DIVISOR_CV---
    (Texto do Novo CV em Markdown)
    
    ---DIVISOR_DADOS---
    CANDIDATO: (1 frase do perfil atual)
    VAGA: (1 frase da vaga)
    MUDANCA: (O que foi priorizado)
    
    ENTRADA:
    CV: {dados_cv}
    VAGA: {dados_vaga}
    """
    return model.generate_content(prompt).text

# ---------------- INTERFACE ----------------
st.title("🎯 Otimizador de Currículo Express")
st.markdown("""
<div class="hero-box">
    <h3>Como funciona:</h3>
    O Agente analisa seu perfil contra a vaga alvo e gera uma nova versão estratégica 
    sem inventar dados, garantindo fidelidade e foco nos requisitos da vaga.
</div>
""", unsafe_allow_html=True)

col_a, col_b = st.columns(2)
with col_a:
    st.subheader("1. Seus Dados")
    user_email = st.text_input("E-mail", placeholder="ex: joao@email.com")
    user_pdf = st.file_uploader("Seu Currículo (PDF)", type="pdf")
with col_b:
    st.subheader("2. A Vaga Alvo")
    job_desc = st.text_area("Descrição da Vaga", height=230, placeholder="Cole aqui os requisitos...")

st.divider()
aceito = st.checkbox("Aceito compartilhar dados para análise.")

# ---------------- BOTÃO MÁGICO ----------------
if st.button("🚀 Gerar Diagnóstico + Novo Currículo"):
    if not (user_email and user_pdf and job_desc and aceito):
        st.warning("⚠️ Preencha todos os campos e aceite os termos.")
    else:
        with st.spinner("🤖 O Agente está redesenhando sua estratégia..."):
            texto_extraido = extrair_texto_pdf(user_pdf)
            
            if texto_extraido in ["ERRO_VAZIO", "ERRO_LEITURA"]:
                st.error("Não conseguimos ler seu PDF. Tente um arquivo com texto selecionável.")
            else:
                try:
                    res_ia = chamar_ia(texto_extraido, job_desc)
                    
                    # Parsing Robusto
                    p_cv = res_ia.split("---DIVISOR_CV---")
                    txt_analise = p_cv[0].strip()
                    resto = p_cv[1] if len(p_cv) > 1 else ""
                    
                    p_dados = resto.split("---DIVISOR_DADOS---")
                    txt_novo_cv = p_dados[0].strip()
                    bloco_meta = p_dados[1] if len(p_dados) > 1 else ""

                    score = extrair_nota_robusta(txt_analise)
                    m_cand, m_vaga, m_mud = "N/A", "N/A", "N/A"
                    for linha in bloco_meta.split('\n'):
                        l = linha.strip()
                        if "CANDIDATO:" in l: m_cand = l.split(":", 1)[1].strip()
                        if "VAGA:" in l: m_vaga = l.split(":", 1)[1].strip()
                        if "MUDANCA:" in l or "MUDANÇA:" in l: m_mud = l.split(":", 1)[1].strip()

                    # --- ENTREGA DE RESULTADOS ---
                    st.success(f"### 🎯 Resultado: {score}% de Compatibilidade")
                    
                    aba_diagnostico, aba_curriculo = st.tabs(["📊 Diagnóstico", "📄 Novo Currículo"])
                    
                    with aba_diagnostico:
                        c1, c2 = st.columns(2)
                        with c1:
                            st.info(f"**Seu Perfil:**\n\n{limpar_markdown_resumo(m_cand)}")
                        with c2:
                            st.warning(f"**O que mudou:**\n\n{limpar_markdown_resumo(m_mud)}")
                        
                        st.divider()
                        st.markdown("#### Análise Completa")
                        st.write(txt_analise)

                    with aba_curriculo:
                        st.info("✨ Currículo otimizado com sucesso! Veja a prévia abaixo e utilize o campo de texto para cópia.")
                        
                        # Preview Formatado
                        with st.container(border=True):
                            st.markdown(txt_novo_cv)
                        
                        st.divider()
                        st.subheader("📥 Levar para o seu editor")
                        st.caption("Clique no ícone de cópia no campo abaixo para levar o texto limpo para o Word/Docs:")
                        st.text_area("Texto Otimizado (Copie aqui):", value=txt_novo_cv, height=400)
                        
                        st.download_button(
                            "Baixar como Arquivo .txt", 
                            txt_novo_cv, 
                            file_name=f"CV_Otimizado_{datetime.now().strftime('%d%m%Y')}.txt"
                        )

                    # Salvamento no Banco
                    salvar_no_sheets(user_email, score, m_cand, m_vaga, m_mud, txt_analise, txt_novo_cv)
                    st.balloons()

                except Exception as e:
                    st.error(f"Erro no processamento da IA: {e}")
