const chatLogEl = document.getElementById("chatLog");
const uiTitleEl = document.getElementById("uiTitle");
const userInputEl = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");
const quitBtn = document.getElementById("quitBtn");
const statusEl = document.getElementById("status");

// 页面可配置文案：修改这里即可
const UI_TEXT = {
  title: "你可以在这里与星辰猫猫对话，而且不需要猫粮哦",
};

if (uiTitleEl) {
  uiTitleEl.textContent = UI_TEXT.title;
}

const API_CHAT = `${location.origin}/chat`;
const API_SHUTDOWN = `${location.origin}/shutdown`;

let sending = false;

userInputEl.addEventListener("keydown", (event) => {
  // Enter 发送；Shift+Enter 换行
  if (event.key !== "Enter") return;
  if (event.shiftKey) return;

  // 中文输入法组合输入时，避免误触发发送
  if (event.isComposing || event.keyCode === 229) return;

  event.preventDefault();
  sendMessage();
});

function appendMessage(role, content) {
  const msgEl = document.createElement("div");
  msgEl.className = `msg ${role === "user" ? "msg-user" : "msg-agent"}`;

  const roleEl = document.createElement("div");
  roleEl.className = "msg-role";
  roleEl.textContent = role === "user" ? "你" : "星辰猫猫";

  const contentEl = document.createElement("div");
  contentEl.className = "msg-content";
  contentEl.textContent = content;

  msgEl.appendChild(roleEl);
  msgEl.appendChild(contentEl);
  chatLogEl.appendChild(msgEl);
  chatLogEl.scrollTop = chatLogEl.scrollHeight;
}

async function sendMessage() {
  if (sending) return;

  const text = userInputEl.value.trim();
  if (!text) {
    statusEl.textContent = "请输入内容。";
    return;
  }

  sending = true;
  sendBtn.disabled = true;
  quitBtn.disabled = true;
  statusEl.textContent = "发送中…";

  appendMessage("user", text);
  userInputEl.value = "";

  try {
    const response = await fetch(API_CHAT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });

    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "请求失败");
    }

    appendMessage("agent", payload.reply || "");
    statusEl.textContent = "完成。";
  } catch (error) {
    statusEl.textContent = `错误：${error.message}`;
  } finally {
    sending = false;
    sendBtn.disabled = false;
    quitBtn.disabled = false;
    userInputEl.focus();
  }
}

async function quit() {
  if (sending) return;

  sending = true;
  sendBtn.disabled = true;
  quitBtn.disabled = true;
  statusEl.textContent = "退出中…";

  try {
    await fetch(API_SHUTDOWN, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
  } catch (_) {
    // ignore
  }

  statusEl.textContent = "已退出。";
  try {
    window.close();
  } catch (_) {
    // ignore
  }
}

sendBtn.addEventListener("click", sendMessage);
quitBtn.addEventListener("click", quit);
