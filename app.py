import streamlit as st
import requests
from search_pb2 import SearchRequest, SearchResponse
from base64 import b64decode
from urllib.parse import urlparse, unquote
import os

st.set_page_config(page_title="Reconhecimento Facial", layout="centered")

# IDs fixos
CLIENT_ID = "6d49da22-41cf-4f68-9eb2-a5d282b9b52f"
COLLECTION_ID = "d7737085-3917-439d-a76e-827c914e69ed"
API_URL = "https://x651fqoqld.execute-api.us-east-1.amazonaws.com/dev/recognize_face"

# Inicializa estados
for key in ["image_bytes", "status", "matches", "fase"]:
    if key not in st.session_state:
        st.session_state[key] = None if key == "image_bytes" else "inicio" if key == "fase" else []

def enviar_reconhecimento(user_id: str, image_bytes: bytes):
    req = SearchRequest(
        image=image_bytes,
        user_id=user_id,
        client_id=CLIENT_ID,
        collection_id=COLLECTION_ID,
    )
    headers = {"Content-Type": "application/octet-stream"}
    response = requests.post(API_URL, data=req.SerializeToString(), headers=headers)

    if response.status_code != 200:
        raise ValueError(f"Erro HTTP {response.status_code}: {response.text}")

    # Trata base64 caso venha do API Gateway
    if response.headers.get("Content-Type", "").startswith("application/json"):
        resp_bytes = b64decode(response.json()["body"])
    else:
        resp_bytes = response.content

    resp = SearchResponse()
    resp.ParseFromString(resp_bytes)
    return resp

# ---------------------------
# FLUXO DO APP
# ---------------------------
st.title("📷 Reconhecimento Facial")

if st.session_state["fase"] == "inicio":
    user_id = st.text_input("🧑 ID do Usuário", "usuario_teste")
    st.session_state["user_id"] = user_id

    foto = st.camera_input("Tire uma foto com seu rosto visível ou escolha da galeria")
    if foto:
        st.session_state["image_bytes"] = foto.getvalue()
        st.session_state["fase"] = "confirmar"

elif st.session_state["fase"] == "confirmar":
    st.image(st.session_state["image_bytes"], caption="Pré-visualização", width=300)
    st.markdown("### A imagem está **nítida e com seu rosto visível**?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("👍 Sim, continuar"):
            st.session_state["fase"] = "buscando"
    with col2:
        if st.button("❌ Não, tirar outra"):
            st.session_state["image_bytes"] = None
            st.session_state["fase"] = "inicio"

elif st.session_state["fase"] == "buscando":
    with st.spinner("🔍 Buscando rostos semelhantes..."):
        try:
            resultado = enviar_reconhecimento(
                st.session_state["user_id"], st.session_state["image_bytes"]
            )
            st.session_state["matches"] = resultado.matches
            st.session_state["status"] = resultado.status
            st.session_state["fase"] = "resultado"
        except Exception as e:
            st.error(f"❌ Erro ao processar a imagem: {e}")
            st.session_state["fase"] = "inicio"

elif st.session_state["fase"] == "resultado":
    st.success(f"✅ Status: {st.session_state['status']}")
    if not st.session_state["matches"]:
        st.warning("Nenhuma face correspondente encontrada.")
    else:
        st.markdown("### 🎯 Resultados encontrados:")
        cols = st.columns(3)
        for idx, match in enumerate(st.session_state["matches"]):
            with cols[idx % 3]:
                st.image(match.image_url, width=200)
                st.caption(f"Similaridade: {match.similarity:.2f}%")

    if st.button("🔁 Tentar outra imagem"):
        st.session_state["image_bytes"] = None
        st.session_state["fase"] = "inicio"
        st.session_state["matches"] = []
