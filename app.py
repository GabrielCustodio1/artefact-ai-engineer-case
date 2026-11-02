import streamlit as st
from agent import responder_mensagem

st.set_page_config(
    page_title="Empório da Música - Atendimento",
    page_icon="🎸",
    layout="centered",
)

st.title("🎸 Empório da Música")
st.caption(
    "Assistente virtual oficial - Instrumentos musicais, pedidos e políticas da loja"
)

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Como posso ajudar você hoje?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Consultando dados da loja..."):
            resposta = responder_mensagem(st.session_state.messages)
            st.markdown(resposta)
            st.session_state.messages.append(
                {"role": "assistant", "content": resposta}
            )
