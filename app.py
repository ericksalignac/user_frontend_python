import streamlit as st
import requests
from search_pb2 import SearchRequest, SearchResponse
from base64 import b64decode
from urllib.parse import unquote, urlparse
import os

st.set_page_config(page_title="Reconhecimento Facial", layout="wide")

# IDs fixos
CLIENT_ID = "6d49da22-41cf-4f68-9eb2-a5d282b9b52f"
COLLECTION_ID = "d7737085-3917-439d-a76e-827c914e69ed"
API_URL = "https://x651fqoqld.execute-api.us-east-1.amazonaws.com/dev/recognize_face"

# SessionState
if "image_bytes" not in st.session_state:
    st.session_state.image_bytes = None
if "mostrar_modal" not in st.session_state:
    st.session_state.mostrar_modal = False
if "processar_imagem" not in st.session_state:
    st.session_state.processar_imagem = False


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
    st.write("Escolha ou tire uma foto nítida com seu rosto visível.")

    user_id = st.text_input("🧑 ID do Usuário", "usuario_teste")

    modo = st.radio("🖼️ Como deseja enviar a imagem?", ["Escolher foto", "Tirar foto com webcam (caso esteja acessando pelo computador ou celular)"])

    image_bytes = None

    if modo == "Escolher foto":
        uploaded_file = st.file_uploader("📁 Selecione uma imagem", type=["jpg", "jpeg", "png"])
        if uploaded_file is not None:
            st.session_state.image_bytes = uploaded_file.read()

    else:
        photo = st.camera_input("📸 Tire uma foto")
        if photo is not None:
            st.session_state.image_bytes = photo.getvalue()

    # Exibe pré-visualização e botão de confirmação
    if st.session_state.image_bytes:
        st.image(st.session_state.image_bytes, caption="Pré-visualização da imagem", width=300)

        if st.button("✅ Confirmar imagem"):
            st.session_state.mostrar_modal = True

    if st.session_state.mostrar_modal:
        st.markdown("---")
        st.markdown("### ⚠️ A imagem está nítida e com seu rosto visível?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("👍 Sim, continuar"):
                st.session_state.processar_imagem = True
                st.session_state.mostrar_modal = False
        with col2:
            if st.button("❌ Não, voltar"):
                st.session_state.image_bytes = None
                st.session_state.mostrar_modal = False

    if st.session_state.processar_imagem:
        with st.spinner("⏳ Buscando imagens semelhantes..."):
            try:
                resultado = enviar_reconhecimento(API_URL, user_id, st.session_state.image_bytes)
                st.success(f"✅ Status: {resultado.status}")
                st.session_state.processar_imagem = False

                if not resultado.matches:
                    st.warning("Nenhuma face correspondente encontrada.")
                else:
                    st.markdown("### 🎯 Resultados encontrados:")
                    cols = st.columns(3)
                    for idx, match in enumerate(resultado.matches):
                        parsed_url = urlparse(match.image_url)
                        file_name = os.path.basename(unquote(parsed_url.path))
                        with cols[idx % 3]:
                            st.image(match.image_url, width=200)
                            st.caption(f"📁 {file_name}\n🔁 Similaridade: {match.similarity:.2f}%")

            except Exception as e:
                st.session_state.processar_imagem = False
                st.error(f"❌ Erro ao processar a resposta: {e}")


if __name__ == "__main__":
    main()
