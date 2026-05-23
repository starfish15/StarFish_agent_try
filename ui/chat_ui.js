const chatLogEl = document.getElementById("chatLog");
const uiTitleEl = document.getElementById("uiTitle");
const subtitleEl = document.getElementById("subtitle");
const userInputEl = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");
const quitBtn = document.getElementById("quitBtn");
const statusEl = document.getElementById("status");
const modeTitleEl = document.getElementById("modeTitle");
const modeButtons = document.querySelectorAll(".mode-btn[data-mode]");
const personaBtn = document.getElementById("personaBtn");
const personaModal = document.getElementById("personaModal");
const personaListEl = document.getElementById("personaList");
const personaStatusEl = document.getElementById("personaStatus");
const personaActiveEl = document.getElementById("personaActive");

// 页面可配置文案：修改这里即可
const UI_TEXT = {
  title: "你可以在这里与星辰猫猫对话，而且不需要猫粮哦",
  subtitle: {
    normal: "你现在是在跟猫猫对话呢（0v0）",
    think: "可恶的理性开发者啊，你要看透猫猫的本质吗？",
    inner: "猫猫会想些什么呢？",
  },
  inputPlaceholder: {
    normal: "在这里输入，然后点击“发送”或按 Enter 键…",
    think: "在这里输入（该模式会显示模型思考摘要与最终回复）…",
    inner: "在这里输入（你会知道猫猫在想什么哦）…",
  },
  thoughtTitle: {
    think: "思考摘要",
    inner: "猫猫的思考",
  },
  thoughtFallback: {
    think: "（未提供思考摘要）",
    inner: "（未提供心里活动）",
  },
};

if (uiTitleEl) {
  uiTitleEl.textContent = UI_TEXT.title;
}

let currentMode = "normal";
const initialActive = Array.from(modeButtons).find((btn) =>
  btn.classList.contains("active")
);
if (initialActive) {
  currentMode = initialActive.dataset.mode || "normal";
}
updateModeTitle();
updateModeButtons();

let personaCache = [];
let activePersona = null;

function setPersonaModalOpen(open) {
  if (!personaModal) return;
  personaModal.classList.toggle("open", open);
  personaModal.setAttribute("aria-hidden", open ? "false" : "true");
}

function updatePersonaActiveLabel() {
  if (!personaActiveEl) return;
  const active = personaCache.find((p) => p.name === activePersona);
  if (active) {
    const label = active.display_name || active.name;
    personaActiveEl.textContent = `当前：${label}`;
  } else {
    personaActiveEl.textContent = "";
  }
}

function renderPersonaList() {
  if (!personaListEl) return;
  personaListEl.innerHTML = "";
  personaCache.forEach((persona) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "persona-btn";
    if (persona.name === activePersona) {
      button.classList.add("active");
    }
    const label = persona.display_name || persona.name;
    const desc = persona.description || "";
    button.innerHTML = `
      <span class="persona-name">${label}</span>
      <span class="persona-desc">${desc}</span>
    `;
    button.addEventListener("click", () => selectPersona(persona.name));
    personaListEl.appendChild(button);
  });
}

async function loadPersonas(options = {}) {
  const showStatus = options.showStatus !== false;
  if (personaStatusEl && showStatus) {
    personaStatusEl.textContent = "加载人设中…";
  }
  try {
    const response = await fetch(API_PERSONAS);
    if (!response.ok) {
      throw new Error("无法加载人设列表");
    }
    const payload = await response.json();
    personaCache = Array.isArray(payload.personas) ? payload.personas : [];
    activePersona = payload.active || null;
    renderPersonaList();
    updatePersonaActiveLabel();
    if (personaStatusEl && showStatus) {
      personaStatusEl.textContent = "";
    }
  } catch (error) {
    if (personaStatusEl && showStatus) {
      personaStatusEl.textContent = error.message || "加载失败";
    }
  }
}

async function selectPersona(name) {
  if (!personaStatusEl) return;
  personaStatusEl.textContent = "切换人设中…";
  try {
    const response = await fetch(API_PERSONA_SELECT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.error || "切换失败");
    }
    const payload = await response.json();
    personaCache = Array.isArray(payload.personas) ? payload.personas : personaCache;
    activePersona = payload.active || name;
    renderPersonaList();
    updatePersonaActiveLabel();
    personaStatusEl.textContent = "";
  } catch (error) {
    personaStatusEl.textContent = error.message || "切换失败";
  }
}

modeButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    setMode(btn.dataset.mode || "normal");
  });
});

if (personaBtn) {
  personaBtn.addEventListener("click", () => {
    setPersonaModalOpen(true);
    loadPersonas();
  });
}

if (personaModal) {
  personaModal.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    if (target.dataset.close === "true") {
      setPersonaModalOpen(false);
    }
  });
}

loadPersonas({ showStatus: false });

const API_CHAT = `${location.origin}/chat_stream`;
const API_SHUTDOWN = `${location.origin}/shutdown`;
const API_PERSONAS = `${location.origin}/personas`;
const API_PERSONA_SELECT = `${location.origin}/select_persona`;

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
  return contentEl;
}

function appendAgentThoughtMessage(thoughtTitleText) {
  const msgEl = document.createElement("div");
  msgEl.className = "msg msg-agent";

  const roleEl = document.createElement("div");
  roleEl.className = "msg-role";
  roleEl.textContent = "星辰猫猫";

  const contentEl = document.createElement("div");
  contentEl.className = "msg-content";

  const thoughtBox = document.createElement("div");
  thoughtBox.className = "thought-box";

  const thoughtTitle = document.createElement("div");
  thoughtTitle.className = "thought-title";
  thoughtTitle.textContent = thoughtTitleText || "思考摘要";

  const thoughtText = document.createElement("div");
  thoughtText.className = "thought-text";

  thoughtBox.appendChild(thoughtTitle);
  thoughtBox.appendChild(thoughtText);

  const finalBox = document.createElement("div");
  finalBox.className = "final-box";

  const finalText = document.createElement("div");
  finalText.className = "final-text";

  finalBox.appendChild(finalText);

  contentEl.appendChild(thoughtBox);
  contentEl.appendChild(finalBox);

  msgEl.appendChild(roleEl);
  msgEl.appendChild(contentEl);
  chatLogEl.appendChild(msgEl);
  chatLogEl.scrollTop = chatLogEl.scrollHeight;

  return { thoughtText, finalText };
}

function getSelectedMode() {
  return currentMode;
}

function setMode(mode) {
  currentMode = mode || "normal";
  updateModeTitle();
  updateModeButtons();
}

function updateModeButtons() {
  modeButtons.forEach((btn) => {
    const isActive = btn.dataset.mode === currentMode;
    btn.classList.toggle("active", isActive);
    btn.setAttribute("aria-pressed", isActive ? "true" : "false");
  });
}

function updateModeTitle() {
  const mode = getSelectedMode();
  if (modeTitleEl) {
    modeTitleEl.textContent = UI_TEXT.modeTitle[mode] || "";
  }
  if (subtitleEl) {
    subtitleEl.textContent = UI_TEXT.subtitle[mode] || "";
  }
  if (userInputEl) {
    userInputEl.placeholder = UI_TEXT.inputPlaceholder[mode] || "";
  }
}

function createThinkStreamRenderer(thoughtEl, finalEl, emptyThoughtText) {
  const THOUGHT_START = "<THOUGHT>";
  const THOUGHT_END = "</THOUGHT>";
  const FINAL_START = "<FINAL>";
  const FINAL_END = "</FINAL>";

  let buffer = "";
  let state = "pre";
  let thought = "";
  let final = "";
  let sawTag = false;

  function update() {
    thoughtEl.textContent = thought.trim();
    finalEl.textContent = final.trim();
    chatLogEl.scrollTop = chatLogEl.scrollHeight;
  }

  function stripTagTokens(text) {
    return text
      .replace(/<\/?\s*thought\s*>/gi, "")
      .replace(/<\/?\s*final\s*>/gi, "");
  }

  function processBuffer() {
    let progressed = true;
    while (progressed) {
      progressed = false;

      if (state === "pre") {
        const thoughtIdx = buffer.indexOf(THOUGHT_START);
        const finalIdx = buffer.indexOf(FINAL_START);
        if (thoughtIdx !== -1) {
          sawTag = true;
          buffer = buffer.slice(thoughtIdx + THOUGHT_START.length);
          state = "thought";
          progressed = true;
          continue;
        }
        if (finalIdx !== -1) {
          sawTag = true;
          buffer = buffer.slice(finalIdx + FINAL_START.length);
          state = "final";
          progressed = true;
          continue;
        }
      }

      if (state === "thought") {
        const endIdx = buffer.indexOf(THOUGHT_END);
        const finalIdx = buffer.indexOf(FINAL_START);

        if (finalIdx !== -1 && (endIdx === -1 || finalIdx < endIdx)) {
          thought += stripTagTokens(buffer.slice(0, finalIdx));
          buffer = buffer.slice(finalIdx + FINAL_START.length);
          state = "final";
          progressed = true;
          continue;
        }
        if (endIdx !== -1) {
          thought += stripTagTokens(buffer.slice(0, endIdx));
          buffer = buffer.slice(endIdx + THOUGHT_END.length);
          state = "after_thought";
          progressed = true;
          continue;
        }
        thought += stripTagTokens(buffer);
        buffer = "";
      }

      if (state === "after_thought") {
        const finalIdx = buffer.indexOf(FINAL_START);
        if (finalIdx !== -1) {
          buffer = buffer.slice(finalIdx + FINAL_START.length);
          state = "final";
          progressed = true;
          continue;
        }
      }

      if (state === "final") {
        const thoughtIdx = buffer.indexOf(THOUGHT_START);
        const endIdx = buffer.indexOf(FINAL_END);

        if (thoughtIdx !== -1 && (endIdx === -1 || thoughtIdx < endIdx)) {
          final += stripTagTokens(buffer.slice(0, thoughtIdx));
          buffer = buffer.slice(thoughtIdx + THOUGHT_START.length);
          state = "thought_after_final";
          progressed = true;
          continue;
        }
        if (endIdx !== -1) {
          final += stripTagTokens(buffer.slice(0, endIdx));
          buffer = buffer.slice(endIdx + FINAL_END.length);
          state = "done";
          progressed = true;
          continue;
        }
        final += stripTagTokens(buffer);
        buffer = "";
      }

      if (state === "thought_after_final") {
        const endIdx = buffer.indexOf(THOUGHT_END);
        if (endIdx !== -1) {
          thought += stripTagTokens(buffer.slice(0, endIdx));
          buffer = buffer.slice(endIdx + THOUGHT_END.length);
          state = "done";
          progressed = true;
          continue;
        }
        thought += stripTagTokens(buffer);
        buffer = "";
      }

      if (state === "done") {
        const thoughtIdx = buffer.indexOf(THOUGHT_START);
        if (thoughtIdx !== -1) {
          buffer = buffer.slice(thoughtIdx + THOUGHT_START.length);
          state = "thought_after_final";
          progressed = true;
          continue;
        }
        final += stripTagTokens(buffer);
        buffer = "";
      }
    }
    update();
  }

  return {
    push(chunk) {
      buffer += chunk;
      processBuffer();
    },
    finalize() {
      if (!sawTag) {
        final += stripTagTokens(buffer);
        buffer = "";
      } else if (state !== "done" && buffer) {
        final += stripTagTokens(buffer);
        buffer = "";
      }
      if (!thought.trim()) {
        thought = emptyThoughtText || "（未提供思考摘要）";
      }
      update();
    },
  };
}

function parseThinkFromFullText(text, emptyThoughtText) {
  const upper = text.toUpperCase();
  const thoughtStart = upper.indexOf("<THOUGHT>");
  const thoughtEnd = upper.indexOf("</THOUGHT>");
  const finalStart = upper.indexOf("<FINAL>");
  const finalEnd = upper.indexOf("</FINAL>");

  let thought = "";
  let final = "";

  if (finalStart !== -1) {
    const start = finalStart + "<FINAL>".length;
    const end = finalEnd !== -1 ? finalEnd : text.length;
    final = text.slice(start, end);
  } else {
    final = text;
  }

  if (thoughtStart !== -1) {
    const start = thoughtStart + "<THOUGHT>".length;
    const end = thoughtEnd !== -1 ? thoughtEnd : (finalStart !== -1 ? finalStart : text.length);
    thought = text.slice(start, end);
  }

  const strip = (value) =>
    value
      .replace(/<\/?\s*thought\s*>/gi, "")
      .replace(/<\/?\s*final\s*>/gi, "")
      .trim();

  thought = strip(thought);
  final = strip(final);

  if (!final) {
    final = strip(text);
  }
  if (!thought) {
    thought = emptyThoughtText || "（未提供思考摘要）";
  }

  return { thought, final };
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
    const mode = getSelectedMode();
    const response = await fetch(API_CHAT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, mode }),
    });

    if (!response.ok) {
      const contentType = response.headers.get("Content-Type") || "";
      if (contentType.includes("application/json")) {
        const payload = await response.json();
        throw new Error(payload.error || payload.detail || "请求失败");
      }
      const errText = await response.text();
      throw new Error(errText || "请求失败");
    }

    if (!response.body) {
      throw new Error("浏览器不支持流式响应");
    }

    let thoughtRenderer = null;
    let agentContentEl = null;
    let thoughtNodes = null;
    if (mode === "think" || mode === "inner") {
      const thoughtTitle = UI_TEXT.thoughtTitle[mode] || "思考摘要";
      const thoughtFallback = UI_TEXT.thoughtFallback[mode] || "（未提供思考摘要）";
      thoughtNodes = appendAgentThoughtMessage(thoughtTitle);
      thoughtRenderer = createThinkStreamRenderer(
        thoughtNodes.thoughtText,
        thoughtNodes.finalText,
        thoughtFallback
      );
    } else {
      agentContentEl = appendMessage("agent", "");
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let reply = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      if (!chunk) continue;
      reply += chunk;
      if ((mode === "think" || mode === "inner") && thoughtRenderer) {
        thoughtRenderer.push(chunk);
      } else {
        agentContentEl.textContent = reply;
      }
      chatLogEl.scrollTop = chatLogEl.scrollHeight;
    }

    const tail = decoder.decode();
    if (tail) {
      reply += tail;
      if ((mode === "think" || mode === "inner") && thoughtRenderer) {
        thoughtRenderer.push(tail);
      } else {
        agentContentEl.textContent = reply;
      }
    }
    if ((mode === "think" || mode === "inner") && thoughtRenderer) {
      thoughtRenderer.finalize();
      if (thoughtNodes) {
        const thoughtFallback = UI_TEXT.thoughtFallback[mode] || "（未提供思考摘要）";
        const parsed = parseThinkFromFullText(reply, thoughtFallback);
        thoughtNodes.thoughtText.textContent = parsed.thought;
        thoughtNodes.finalText.textContent = parsed.final;
      }
    }
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
