import streamlit as st
from agent import responder_mensagem

st.set_page_config(
    page_title="Empório da Música - Atendimento Virtual",
    page_icon="🎸",
    layout="centered",
)

st.title("🎸 Empório da Música")
st.caption(
    "Assistente virtual especializado em instrumentos musicais, pedidos e políticas da loja."
)

# Inicializa o histórico na sessão do Streamlit
if "messages" not in st.session_state:
    st.session_state.messages = []

# Exibe as mensagens trocadas anteriormente
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Captura nova entrada do usuário
if prompt := st.chat_input("Digite sua dúvida sobre produtos, pedidos ou políticas..."):
    # Renderiza e salva mensagem do usuário
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Gera a resposta do agente
    with st.chat_message("assistant"), st.spinner("Consultando dados da loja..."):
        resposta = responder_mensagem(st.session_state.messages)
        st.markdown(resposta)

    # Salva a resposta no histórico da conversa
    st.session_state.messages.append({"role": "assistant", "content": resposta})
