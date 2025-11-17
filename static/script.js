const chatToggle = document.getElementById("chat-toggle");
const chatContainer = document.getElementById("chat-container");
const chatMessages = document.getElementById("chat-messages");
const chatInput = document.getElementById("chat-input");
const chatSend = document.getElementById("chat-send");

chatToggle.addEventListener("click", () => {
  chatContainer.classList.toggle("open");
});

chatSend.addEventListener("click", sendMessage);
chatInput.addEventListener("keypress", e => {
  if (e.key === "Enter") sendMessage();
});


// -------------------------------
// Função segura de criação de mensagens
// -------------------------------
function createBotMessage(text) {
  const botMsg = document.createElement("div");
  botMsg.className = "bot-msg";

  // Processar mensagem sem usar innerHTML
  const parts = text.split(/(https?:\/\/[^\s]+)/g);

  parts.forEach(part => {
    if (/^https?:\/\//.test(part)) {
      // Criar link seguro
      const a = document.createElement("a");
      a.href = part;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.textContent = part;
      botMsg.appendChild(a);
    } else {
      // Adicionar apenas texto normal
      botMsg.appendChild(document.createTextNode(part));
    }
  });

  return botMsg;
}


// -------------------------------
// Função principal de envio
// -------------------------------
function sendMessage() {
  const text = chatInput.value.trim();
  if (!text) return;

  // Mensagem do usuário
  const userMsg = document.createElement("div");
  userMsg.className = "user-msg";
  userMsg.textContent = text;
  chatMessages.appendChild(userMsg);

  chatInput.value = "";

  // Mensagem temporária do bot
  const loadingMsg = document.createElement("div");
  loadingMsg.className = "bot-msg";
  loadingMsg.textContent = "Carregando resposta...";
  chatMessages.appendChild(loadingMsg);

  chatMessages.scrollTop = chatMessages.scrollHeight;

  // Envia a requisição
  fetch("/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question: text })
  })
    .then(res => res.json())
    .then(data => {
      const resposta = data.answer || "Não consegui responder.";

      // Remove mensagem de carregamento
      loadingMsg.remove();

      // Cria mensagem segura do bot
      const botMsg = createBotMessage(resposta);
      chatMessages.appendChild(botMsg);

      chatMessages.scrollTop = chatMessages.scrollHeight;
    })
    .catch(() => {
      loadingMsg.textContent = "Erro ao conectar com o servidor.";
    });
}
