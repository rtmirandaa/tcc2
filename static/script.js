// static/script.js

const chatToggle = document.getElementById("chat-toggle");
const chatContainer = document.getElementById("chat-container");
const chatMessages = document.getElementById("chat-messages");
const chatInput = document.getElementById("chat-input");
const chatSend = document.getElementById("chat-send");

// ----------------------------------------------------------
// Abertura/fechamento do chat
// ----------------------------------------------------------
chatToggle.addEventListener("click", () => {
  chatContainer.classList.toggle("open");
  if (chatContainer.classList.contains("open")) {
    chatInput.focus();
  }
});

chatSend.addEventListener("click", sendMessage);

chatInput.addEventListener("keypress", e => {
  if (e.key === "Enter") {
    e.preventDefault();
    sendMessage();
  }
});


// ----------------------------------------------------------
// Função segura para criar mensagens do bot
// (remove innerHTML e mantém links clicáveis com segurança)
// ----------------------------------------------------------
function createBotMessage(text) {
  const botMsg = document.createElement("div");
  botMsg.className = "bot-msg";

  // Divide a mensagem com base em URLs detectadas
  const parts = text.split(/(https?:\/\/[^\s]+)/g);

  parts.forEach(part => {
    if (/^https?:\/\//.test(part)) {
      const a = document.createElement("a");
      a.href = part;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.textContent = part;
      botMsg.appendChild(a);
    } else {
      botMsg.appendChild(document.createTextNode(part));
    }
  });

  return botMsg;
}


// ----------------------------------------------------------
// Função de scroll automático
// ----------------------------------------------------------
function scrollToBottom() {
  chatMessages.scrollTop = chatMessages.scrollHeight;
}


// ----------------------------------------------------------
// Append de mensagens
// ----------------------------------------------------------
function appendMessage(element) {
  chatMessages.appendChild(element);
  scrollToBottom();
}


// ----------------------------------------------------------
// Envio da pergunta ao backend
// ----------------------------------------------------------
function sendMessage() {
  const text = chatInput.value.trim();
  if (!text) return;

  // Mensagem do usuário
  const userMsg = document.createElement("div");
  userMsg.className = "user-msg";
  userMsg.textContent = text;
  appendMessage(userMsg);

  chatInput.value = "";
  chatInput.focus();

  // Mensagem de carregamento
  const loadingMsg = document.createElement("div");
  loadingMsg.className = "bot-msg";
  loadingMsg.textContent = "Carregando resposta...";
  appendMessage(loadingMsg);

  // Requisição ao backend
  fetch("/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question: text })
  })
    .then(res => {
      if (!res.ok) {
        throw new Error("Falha na requisição ao servidor.");
      }
      return res.json();
    })
    .then(data => {
      loadingMsg.remove();

      const resposta = data?.answer || "Não consegui responder.";
      const botMsg = createBotMessage(resposta);
      appendMessage(botMsg);
    })
    .catch(err => {
      loadingMsg.remove();

      const errorMsg = document.createElement("div");
      errorMsg.className = "bot-msg";
      errorMsg.textContent = "Erro ao conectar ao servidor.";
      appendMessage(errorMsg);

      console.error("Erro:", err);
    });
}
