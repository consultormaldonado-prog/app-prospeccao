import streamlit as st
import pandas as pd
import urllib.parse
import pytesseract
from PIL import Image
import re
import fitz  # Esta é a biblioteca nova para ler PDF
import io

# Configura a página
st.set_page_config(page_title="Prospecção WhatsApp", layout="wide")
st.title("📱 Sistema de Prospecção de Contatos")

# Passo 1: Cadastro da Campanha
st.header("1. Dados da Campanha")
campanha = st.text_input("Qual o foco? (Nome do Imóvel / Veículo / Promoção)")
mensagem_padrao = st.text_area(
    "Mensagem Padrão (O texto que será enviado)", 
    "Olá {nome}! Tudo bem? Vi que você pode se interessar pelo {campanha}. Podemos conversar?"
)
st.info("Dica: Deixe os termos {nome} e {campanha} no texto. O sistema vai trocar isso automaticamente pelos dados de cada cliente!")

# Passo 2: Upload de Arquivos
st.header("2. Lista de Contatos")
arquivo = st.file_uploader(
    "Suba sua planilha, foto ou PDF (Excel, CSV, JPG, PNG, PDF)", 
    type=["xlsx", "csv", "png", "jpg", "jpeg", "pdf"]
)

if arquivo:
    df = None
    texto_extraido = ""
    
    # Verifica qual é o tipo de arquivo
    if arquivo.name.endswith('.csv'):
        df = pd.read_csv(arquivo)
    elif arquivo.name.endswith('.xlsx'):
        df = pd.read_excel(arquivo)
    else:
        # É PDF ou Imagem!
        if arquivo.name.endswith('.pdf'):
            st.info("📄 PDF detectado! Extraindo textos (isso pode levar alguns segundos se tiver muitas páginas)...")
            doc = fitz.open(stream=arquivo.read(), filetype="pdf")
            for page in doc:
                texto_pagina = page.get_text()
                if texto_pagina.strip():
                    texto_extraido += texto_pagina + "\n"
                else:
                    # Se a página do PDF for uma imagem escaneada, usamos o Olho Digital
                    pix = page.get_pixmap(dpi=150)
                    img = Image.open(io.BytesIO(pix.tobytes()))
                    texto_extraido += pytesseract.image_to_string(img, lang='por') + "\n"
        else:
            # É uma foto direta
            st.info("📷 Foto detectada! Extraindo textos...")
            imagem = Image.open(arquivo)
            texto_extraido = pytesseract.image_to_string(imagem, lang='por')
        
        # Mostra o texto bruto
        with st.expander("Ver texto original lido pelo sistema"):
            st.text(texto_extraido)
        
        # Tenta organizar o texto separando Nome e Telefone
        linhas = texto_extraido.split('\n')
        dados = []
        
        for linha in linhas:
            if linha.strip():
                numeros = "".join(re.findall(r'\d', linha))
                if 8 <= len(numeros) <= 13:
                    telefone = numeros
                    nome = re.sub(r'\d', '', linha).strip()
                    nome = re.sub(r'[^a-zA-ZÀ-ÿ\s]', '', nome).strip()
                    dados.append({"Nome": nome, "Telefone": telefone})
                else:
                    nome = re.sub(r'[^a-zA-ZÀ-ÿ\s]', '', linha).strip()
                    if len(nome) > 2:
                        dados.append({"Nome": nome, "Telefone": ""})
        
        df = pd.DataFrame(dados)

    # Se conseguiu criar a tabela, mostra na tela
    if df is not None and not df.empty:
        st.write("### Tabela de Contatos")
        st.write("⚠️ **Importante:** Se subiu um PDF ou Foto, clique na tabela para corrigir letras que o leitor possa ter confundido.")
        
        df_editado = st.data_editor(df, num_rows="dynamic", use_container_width=True)
        
        st.header("3. Enviar Mensagens")
        st.write("Indique em quais colunas da sua lista estão os dados corretos:")
        
        colunas = df_editado.columns.tolist()
        col_nome = st.selectbox("Qual coluna tem o NOME do cliente?", colunas)
        col_telefone = st.selectbox("Qual coluna tem o TELEFONE do cliente?", colunas)

        if st.button("Gerar Botões do WhatsApp"):
            st.write("---")
            for index, row in df_editado.iterrows():
                nome = str(row[col_nome]) if pd.notna(row[col_nome]) else ""
                telefone = str(row[col_telefone]) if pd.notna(row[col_telefone]) else ""
                
                telefone_limpo = re.sub(r'\D', '', telefone)
                
                if telefone_limpo and len(telefone_limpo) >= 8:
                    msg_final = mensagem_padrao.replace("{nome}", nome).replace("{campanha}", campanha)
                    msg_codificada = urllib.parse.quote(msg_final)
                    link_wa = f"https://wa.me/55{telefone_limpo}?text={msg_codificada}"
                    st.markdown(f"**{nome}** ({telefone_limpo}) ➡️ [CLIQUE PARA INICIAR A CONVERSA]({link_wa})")
    else:
        st.warning("Não consegui encontrar nomes ou telefones neste arquivo.")