import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader 
import os
import fitz
import PIL.Image
import time
import tempfile

path2 = tempfile.mkdtemp()

def page_setup():
    st.header("Converse com diferentes tipos de mídia/arquivos!", anchor=False, divider="blue")

    hide_menu_style = """
            <style>
            #MainMenu {visibility: hidden;}
            </style>
            """
    st.markdown(hide_menu_style, unsafe_allow_html=True)

def get_typeofpdf():
    st.sidebar.header("Selecione o tipo de mídia", divider='orange')
    typepdf = st.sidebar.radio("Escolha uma:",
                               ("Arquivos PDF",
                                "Imagens",
                                "Vídeo, arquivo mp4",
                                "Arquivos de áudio"))
    return typepdf

def get_llminfo():
    st.sidebar.header("Opções", divider='rainbow')
    
    api_key = st.sidebar.text_input("Digite sua chave de API do Google:", type="password")
    
    tip1 = "Selecione um modelo que deseja usar."
    model = st.sidebar.radio("Escolha o LLM:",
                                  ("gemini-1.5-flash",
                                   "gemini-1.5-pro",
                                   ), help=tip1)
    tip2 = "Temperaturas mais baixas são boas para prompts que exigem uma resposta menos aberta ou criativa, enquanto temperaturas mais altas podem gerar resultados mais diversos ou criativos. Uma temperatura de 0 significa que os tokens de maior probabilidade são sempre selecionados."
    temp = st.sidebar.slider("Temperatura:", min_value=0.0,
                                    max_value=2.0, value=1.0, step=0.25, help=tip2)
    tip3 = "Usado para amostragem de núcleo. Especifique um valor mais baixo para respostas menos aleatórias e um valor mais alto para respostas mais aleatórias."
    topp = st.sidebar.slider("Top P:", min_value=0.0,
                             max_value=1.0, value=0.94, step=0.01, help=tip3)
    tip4 = "Número de tokens de resposta, 8194 é o limite."
    maxtokens = st.sidebar.slider("Máximo de Tokens:", min_value=100,
                                  max_value=5000, value=2000, step=100, help=tip4)
    return api_key, model, temp, topp, maxtokens

def delete_files_in_directory(directory_path):
   try:
     files = os.listdir(directory_path)
     for file in files:
       file_path = os.path.join(directory_path, file)
       if os.path.isfile(file_path):
         os.remove(file_path)
   except OSError:
     print("Ocorreu um erro ao deletar os arquivos.")

def setup_documents(pdf_file_path):
    to_delete_path = path2
    delete_files_in_directory(to_delete_path)
    doc = fitz.open(pdf_file_path)
    os.chdir(to_delete_path)
    for page in doc: 
        pix = page.get_pixmap(matrix=fitz.Identity, dpi=None, 
                              colorspace=fitz.csRGB, clip=None, alpha=False, annots=True) 
        pix.save("pdfimage-%i.jpg" % page.number)

def save_uploaded_file(uploaded_file):
    if uploaded_file is not None:
        file_path = os.path.join(tempfile.gettempdir(), uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    return None

def main():
    page_setup()
    typepdf = get_typeofpdf()
    api_key, model, temperature, top_p, max_tokens = get_llminfo()
    
    if api_key:
        genai.configure(api_key=api_key)
    else:
        st.warning("Por favor, digite sua chave de API do Google na barra lateral para prosseguir.")
        return

    if typepdf == "Arquivos PDF":
        uploaded_files = st.file_uploader("Escolha 1 ou mais PDFs", type='pdf', accept_multiple_files=True)
           
        if uploaded_files:
            text = ""
            for pdf in uploaded_files:
                pdf_reader = PdfReader(pdf)
                for page in pdf_reader.pages:
                    text += page.extract_text()

            generation_config = {
              "temperature": temperature,
              "top_p": top_p,
              "max_output_tokens": max_tokens,
              "response_mime_type": "text/plain",
              }
            model = genai.GenerativeModel(
              model_name=model,
              generation_config=generation_config,)
            st.write(model.count_tokens(text)) 
            question = st.text_input("Digite sua pergunta e pressione Enter.")
            if question:
                response = model.generate_content([question, text])
                st.write(response.text)
                
    elif typepdf == "Imagens":
        image_file = st.file_uploader("Envie seu arquivo de imagem.")
        if image_file:
            image_path = save_uploaded_file(image_file)
            image_file = genai.upload_file(path=image_path)
            
            while image_file.state.name == "PROCESSING":
                time.sleep(10)
                image_file = genai.get_file(image_file.name)
            if image_file.state.name == "FAILED":
              raise ValueError(image_file.state.name)
            
            prompt2 = st.text_input("Digite seu prompt.") 
            if prompt2:
                generation_config = {
                  "temperature": temperature,
                  "top_p": top_p,
                  "max_output_tokens": max_tokens,}
                model = genai.GenerativeModel(model_name=model, generation_config=generation_config,)
                response = model.generate_content([image_file, prompt2],
                                                  request_options={"timeout": 600})
                st.markdown(response.text)
                
                genai.delete_file(image_file.name)
                print(f'Arquivo deletado {image_file.uri}')
           
    elif typepdf == "Vídeo, arquivo mp4":
        video_file = st.file_uploader("Envie seu vídeo")
        if video_file:
            video_path = save_uploaded_file(video_file)
            video_file = genai.upload_file(path=video_path)
            
            while video_file.state.name == "PROCESSING":
                time.sleep(10)
                video_file = genai.get_file(video_file.name)
            if video_file.state.name == "FAILED":
              raise ValueError(video_file.state.name)
            
            prompt3 = st.text_input("Digite seu prompt.") 
            if prompt3:
                model = genai.GenerativeModel(model_name=model)
                st.write("Fazendo a requisição de inferência ao LLM...")
                response = model.generate_content([video_file, prompt3],
                                                  request_options={"timeout": 600})
                st.markdown(response.text)
                
                genai.delete_file(video_file.name)
                print(f'Arquivo deletado {video_file.uri}')
      
    elif typepdf == "Arquivos de áudio":
        audio_file = st.file_uploader("Envie seu áudio")
        if audio_file:
            audio_path = save_uploaded_file(audio_file)
            audio_file = genai.upload_file(path=audio_path)

            while audio_file.state.name == "PROCESSING":
                time.sleep(10)
                audio_file = genai.get_file(audio_file.name)
            if audio_file.state.name == "FAILED":
              raise ValueError(audio_file.state.name)

            prompt3 = st.text_input("Digite seu prompt.")
            if prompt3:
                model = genai.GenerativeModel(model_name=model)
                response = model.generate_content([audio_file, prompt3],
                                                  request_options={"timeout": 600})
                st.markdown(response.text)
                
                genai.delete_file(audio_file.name)
                print(f'Arquivo deletado {audio_file.uri}')

if __name__ == '__main__':
    main()