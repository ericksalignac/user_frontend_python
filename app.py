# app.py

import streamlit as st
import requests
from search_pb2 import SearchRequest, SearchResponse
from base64 import b64decode
from urllib.parse import unquote, urlparse
import os

st.set_page_config(
    page_title="Reconhecimento Facial", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS personalizado para melhorar a experiência mobile
st.markdown("""
<style>
    /* Melhora a experiência em dispositivos móveis */
    .stFileUploader > div > div > div > div {
        min-height: 60px;
    }
    
    /* Melhora os botões em mobile */
    .stButton > button {
        width: 100%;
        min-height: 50px;
        font-size: 16px;
    }
    
    /* Melhora o input de texto */
    .stTextInput > div > div > input {
        min-height: 50px;
        font-size: 16px;
    }
    
    /* Melhora o radio button */
    .stRadio > div {
        flex-direction: column;
    }
    
    /* Força recarregamento do file uploader */
    .stFileUploader {
        touch-action: manipulation;
    }
    
    /* Melhora a responsividade */
    @media (max-width: 768px) {
        .main .block-container {
            padding-top: 2rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }
        
        .stImage {
            max-width: 100%;
        }
    }
</style>
""", unsafe_allow_html=True)

# IDs fixos
CLIENT_ID = "6d49da22-41cf-4f68-9eb2-a5d282b9b52f"
COLLECTION_ID = "d7737085-3917-439d-a76e-827c914e69ed"
API_URL = "https://x651fqoqld.execute-api.us-east-1.amazonaws.com/dev/recognize_face"

# SessionState para controle do fluxo
if "image_bytes" not in st.session_state:
    st.session_state.image_bytes = None
if "mostrar_modal" not in st.session_state:
    st.session_state.mostrar_modal = False
if "processar_imagem" not in st.session_state:
    st.session_state.processar_imagem = False


def detectar_mobile():
    """Detecta se o usuário está usando um dispositivo móvel"""
    user_agent = st.context.headers.get('user-agent', '').lower()
    mobile_keywords = ['mobile', 'android', 'iphone', 'ipad', 'ipod', 'blackberry', 'windows phone']
    return any(keyword in user_agent for keyword in mobile_keywords)


def enviar_reconhecimento(api_url, user_id, image_bytes):
    req = SearchRequest(
        image=image_bytes,
        user_id=user_id,
        client_id=CLIENT_ID,
        collection_id=COLLECTION_ID,
    )
    headers = {"Content-Type": "application/octet-stream"}
    response = requests.post(api_url, data=req.SerializeToString(), headers=headers)

    if response.status_code != 200:
        raise ValueError(f"Erro HTTP {response.status_code}: {response.text}")

    if response.headers.get("Content-Type", "").startswith("application/json"):
        resp_bytes = b64decode(response.json()["body"])
    else:
        resp_bytes = response.content

    resp = SearchResponse()
    resp.ParseFromString(resp_bytes)
    return resp


def main():
    st.title("🔍 Reconhecimento Facial")
    st.write("Faça upload de uma selfie ou tire uma nova foto para buscar correspondências.")

    # Debug info para mobile (expansível)
    with st.expander("🛠️ Informações de Debug (clique para expandir)"):
        is_mobile = detectar_mobile()
        st.write(f"**Dispositivo móvel detectado:** {'✅ Sim' if is_mobile else '❌ Não'}")
        st.write(f"**User Agent:** {st.context.headers.get('user-agent', 'Não disponível')}")
        st.write(f"**Sessão ativa:** {bool(st.session_state.get('image_bytes'))}")
        if st.session_state.get('image_bytes'):
            st.write(f"**Tamanho da imagem:** {len(st.session_state.image_bytes):,} bytes")
        st.write(f"**Estados:** Modal={st.session_state.get('mostrar_modal', False)}, Processar={st.session_state.get('processar_imagem', False)}")

    user_id = st.text_input("🧑 ID do Usuário", "usuario_teste")

    # Adapta as opções baseado no dispositivo
    is_mobile = detectar_mobile()
    if is_mobile:
        modo_opcoes = ["Tirar nova foto", "Escolher foto da galeria"]
        modo_help = "� Em dispositivos móveis: 'Escolher foto da galeria' abre câmera/galeria, 'Tirar nova foto' usa câmera diretamente"
    else:
        modo_opcoes = ["Tirar foto com webcam", "Escolher foto da galeria"]
        modo_help = "💻 No computador: escolha arquivo ou use a webcam"
    
    modo = st.radio("🖼️ Como deseja enviar a imagem?", modo_opcoes, help=modo_help)

    # Reset do estado quando mudamos de modo
    if "ultimo_modo" not in st.session_state:
        st.session_state.ultimo_modo = modo
    elif st.session_state.ultimo_modo != modo:
        st.session_state.image_bytes = None
        st.session_state.mostrar_modal = False
        st.session_state.processar_imagem = False
        st.session_state.ultimo_modo = modo

    if modo == "Escolher foto da galeria":
        if is_mobile:
            st.info("📱 **Dica para celular:** Ao tocar no botão abaixo, escolha 'Câmera' para tirar uma nova foto ou 'Galeria' para selecionar uma foto existente.")
        
        uploaded_file = st.file_uploader(
            "Selecione uma imagem", 
            type=["jpg", "jpeg", "png"],
            key=f"file_uploader_{'mobile' if is_mobile else 'desktop'}",
            help="📱 Toque aqui para acessar câmera ou galeria" if is_mobile else "Clique para selecionar um arquivo"
        )
        
        if uploaded_file is not None:
            # Força a leitura completa do arquivo com validação extra
            try:
                # Tenta ler o arquivo em chunks para garantir carregamento completo
                file_bytes = uploaded_file.read()
                
                # Validações adicionais
                if not file_bytes:
                    st.error("❌ Erro: arquivo vazio")
                elif len(file_bytes) < 100:  # Muito pequeno para ser uma imagem válida
                    st.error("❌ Erro: arquivo muito pequeno ou corrompido")
                elif len(file_bytes) > 10 * 1024 * 1024:  # Maior que 10MB
                    st.warning("⚠️ Arquivo muito grande. Recomenda-se usar imagens menores que 10MB")
                    st.session_state.image_bytes = file_bytes
                    st.success("✅ Imagem carregada com sucesso!")
                else:
                    st.session_state.image_bytes = file_bytes
                    st.success("✅ Imagem carregada com sucesso!")
                    
            except Exception as e:
                st.error(f"❌ Erro ao ler o arquivo: {e}")
                if is_mobile:
                    st.info("💡 **Dica:** Tente tirar uma nova foto ou escolher outra imagem da galeria")
    else:
        if is_mobile:
            st.info("📱 A câmera será ativada diretamente no seu dispositivo")
        
        image_input = st.camera_input("Capture uma imagem")
        if image_input is not None:
            try:
                image_bytes = image_input.getvalue()
                if image_bytes and len(image_bytes) > 0:
                    st.session_state.image_bytes = image_bytes
                    st.success("✅ Foto capturada com sucesso!")
                else:
                    st.error("❌ Erro: imagem vazia")
            except Exception as e:
                st.error(f"❌ Erro ao capturar imagem: {e}")

    # Verificação de estado da imagem com informações detalhadas
    if st.session_state.image_bytes:
        # Mostra informações sobre o arquivo carregado
        file_size = len(st.session_state.image_bytes)
        st.info(f"📊 Arquivo carregado: {file_size:,} bytes ({file_size/1024:.1f} KB)")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            try:
                st.image(st.session_state.image_bytes, caption="Pré-visualização da imagem", width=300)
            except Exception as e:
                st.error(f"❌ Erro ao exibir imagem: {e}")
                st.session_state.image_bytes = None
        
        with col2:
            if st.button("✅ Confirmar imagem", use_container_width=True):
                st.session_state.mostrar_modal = True
            if st.button("🔄 Carregar nova imagem", use_container_width=True):
                st.session_state.image_bytes = None
                st.session_state.mostrar_modal = False
                st.session_state.processar_imagem = False
                st.rerun()

    # Modal de confirmação mais responsivo
    if st.session_state.mostrar_modal:
        st.markdown("---")
        st.markdown("### ⚠️ Esta imagem está nítida e com o seu rosto visível?")
        st.markdown("🔍 Verifique se:")
        st.markdown("- ✓ O rosto está claramente visível")
        st.markdown("- ✓ A imagem não está borrada")
        st.markdown("- ✓ Há iluminação adequada")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("👍 Sim, continuar", use_container_width=True, type="primary"):
                st.session_state.processar_imagem = True
                st.session_state.mostrar_modal = False
                st.rerun()
        with col2:
            if st.button("❌ Não, voltar", use_container_width=True):
                st.session_state.image_bytes = None
                st.session_state.mostrar_modal = False
                st.rerun()

    # Processamento com melhor feedback
    if st.session_state.processar_imagem:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            status_text.text("🔄 Preparando imagem...")
            progress_bar.progress(25)
            
            status_text.text("🚀 Enviando para reconhecimento...")
            progress_bar.progress(50)
            
            resultado = enviar_reconhecimento(API_URL, user_id, st.session_state.image_bytes)
            progress_bar.progress(75)
            
            status_text.text("✅ Processando resultados...")
            progress_bar.progress(100)
            
            st.success(f"✅ Status: {resultado.status}")
            st.session_state.processar_imagem = False
            
            # Limpa a barra de progresso
            progress_bar.empty()
            status_text.empty()

            if not resultado.matches:
                st.warning("⚠️ Nenhuma face correspondente encontrada.")
                st.info("💡 Dicas: Certifique-se de que o rosto está claramente visível e bem iluminado.")
            else:
                st.markdown("### 🎯 Resultados encontrados:")
                
                # Layout responsivo para resultados
                num_matches = len(resultado.matches)
                if num_matches <= 3:
                    cols = st.columns(num_matches)
                else:
                    cols = st.columns(3)
                
                for idx, match in enumerate(resultado.matches):
                    parsed_url = urlparse(match.image_url)
                    file_name = os.path.basename(unquote(parsed_url.path))
                    with cols[idx % len(cols)]:
                        try:
                            st.image(match.image_url, width=200)
                            st.caption(f"📁 {file_name}\n🔁 Similaridade: {match.similarity:.2f}%")
                        except Exception as img_error:
                            st.error(f"❌ Erro ao carregar imagem: {img_error}")

        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.session_state.processar_imagem = False
            st.error(f"❌ Erro ao processar a resposta: {e}")
            st.info("🔄 Tente novamente ou verifique sua conexão com a internet.")


if __name__ == "__main__":
    main()
