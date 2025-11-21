const chatToggle = document.getElementById("chat-toggle");
const chatContainer = document.getElementById("chat-container");
const chatMessages = document.getElementById("chat-messages");
const chatInput = document.getElementById("chat-input");
const chatSend = document.getElementById("chat-send");

// Abrir/Fechar Chat
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

// --- FUNÇÃO DE FORMATAÇÃO (CIRURGIÃO DE LINKS) ---
function createBotMessage(text) {
  const botMsg = document.createElement("div");
  botMsg.className = "bot-msg";

  let formatted = text;

  // 1. Negrito: **texto** vira <strong>texto</strong>
  formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

  // 2. Listas: " * texto" ou "* texto" vira pular linha + bolinha
  formatted = formatted.replace(/(^|\s)\* (.*?)/g, '\n• $2');

  // 3. LINKS (A CORREÇÃO ESTÁ AQUI)
// Regex para detecção de links
  const urlRegex = /((https?:\/\/|www\.|[\w.-]*\.?ufrgs\.br)[^\s<]*)/g;

  formatted = formatted.replace(urlRegex, (match) => {
    
    let cleanUrl = match.replace(/[.,;>)]+$/, "");                                          // Remove pontuação final

                                                                                            // Remove prefixos incorretos
    if (cleanUrl.startsWith(".")) {cleanUrl = cleanUrl.substring(1);}
    if (cleanUrl.startsWith("1.")) {cleanUrl = cleanUrl.substring(2);}

                                                                                            // Adiciona https
    let href = cleanUrl;
    if (!href.startsWith("http")) {
      href = "https://" + href;
    }

    return `<a href="${href}" target="_blank" rel="noopener noreferrer">${cleanUrl}</a>`;
  });

  botMsg.innerHTML = formatted;
  return botMsg;
}
// -------------------------------------------------

function scrollToBottom() {
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function appendMessage(element) {
  chatMessages.appendChild(element);
  scrollToBottom();
}

function sendMessage() {
  const text = chatInput.value.trim();
  if (!text) return;

  const userMsg = document.createElement("div");
  userMsg.className = "user-msg";
  userMsg.textContent = text;
  appendMessage(userMsg);

  chatInput.value = "";
  chatInput.focus();

  const loadingMsg = document.createElement("div");
  loadingMsg.className = "bot-msg";
  loadingMsg.textContent = "Digitando...";
  appendMessage(loadingMsg);

  fetch("/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question: text })
  })
    .then(res => {
      if (!res.ok) throw new Error("Erro na rede");
      return res.json();
    })
    .then(data => {
      loadingMsg.remove();
      const resposta = data?.answer || "Desculpe, não consegui responder.";
      const botMsg = createBotMessage(resposta);
      appendMessage(botMsg);
    })
    .catch(err => {
      loadingMsg.remove();
      const errorMsg = document.createElement("div");
      errorMsg.className = "bot-msg";
      errorMsg.textContent = "Erro de conexão.";
      appendMessage(errorMsg);
      console.error(err);
    });
}