import streamlit as st
from agent import responder_mensagem

st.set_page_config(
    page_title="Empório da Música - Atendimento", page_icon="🎸", layout="centered"
)

st.title("🎸 Empório da Música")
st.caption(
    "Assistente virtual oficial - Instrumentos musicais, pedidos e políticas da loja"
)

# Inicializa o histórico na sessão
if "messages" not in st.session_state:
    st.session_state.messages = []

# Exibe as mensagens já trocadas
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Entrada do usuário
if prompt := st.chat_input("Como posso ajudar você hoje?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Processamento com indicador visual
    with st.chat_message("assistant"):
        with st.spinner("Consultando dados da loja..."):
            try:
                resposta = responder_mensagem(st.session_state.messages)
            except Exception as e:
                print(f"[Erro no app.py]: {e}")
                resposta = "Desculpe, tive uma oscilação momentânea na conexão. Poderia repetir sua dúvida?"

            st.markdown(resposta)
            st.session_state.messages.append(
                {"role": "assistant", "content": resposta}
            )
