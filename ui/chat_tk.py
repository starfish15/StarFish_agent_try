import os
import sys
import threading
import time

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

try:
    import tkinter as tk
    from tkinter import ttk
    from tkinter.scrolledtext import ScrolledText
except ModuleNotFoundError as exc:
    raise SystemExit(
        "缺少 tkinter：你的系统 Python 未安装 Tk 支持。\n"
        "- Debian/Ubuntu：sudo apt-get install python3-tk\n"
        "- Fedora：sudo dnf install python3-tkinter\n"
        "安装后再运行：uv run ui/chat_tk.py"
    ) from exc

from tkinter import font as tkfont

import requests


def _default_base_url() -> str:
    host = os.getenv("CHAT_CLIENT_HOST", "127.0.0.1")
    port = int(os.getenv("CHAT_PORT", "8002"))
    return f"http://{host}:{port}"


class ChatWindow:
    def __init__(self, root: tk.Tk, base_url: str, started_server: bool, ui_font_family: str):
        self.root = root
        self.base_url = base_url.rstrip("/")
        self.started_server = started_server
        self.sending = False
        self.ui_font_family = ui_font_family

        root.title("StarFish Agent Chat")
        root.geometry("860x640")

        container = ttk.Frame(root, padding=14)
        container.pack(fill=tk.BOTH, expand=True)

        header = ttk.Label(container, text="对话窗口（Tkinter）", font=(self.ui_font_family, 15, "bold"))
        header.pack(anchor="w")

        self.chat_log = ScrolledText(container, wrap=tk.WORD, height=22)
        self.chat_log.pack(fill=tk.BOTH, expand=True, pady=(10, 12))
        self.chat_log.configure(state=tk.DISABLED)

        input_label = ttk.Label(container, text="你的输入")
        input_label.pack(anchor="w")

        self.input_text = tk.Text(container, height=4, wrap=tk.WORD)
        self.input_text.pack(fill=tk.X, expand=False, pady=(6, 10))

        controls = ttk.Frame(container)
        controls.pack(fill=tk.X)

        self.send_btn = ttk.Button(controls, text="发送", command=self.send)
        self.send_btn.pack(side=tk.LEFT)

        self.quit_btn = ttk.Button(controls, text="退出", command=self.quit)
        self.quit_btn.pack(side=tk.LEFT, padx=(10, 0))

        self.status = ttk.Label(container, text="")
        self.status.pack(anchor="w", pady=(10, 0))

        self._append("系统", f"已连接：{self.base_url}")

    def _append(self, role: str, content: str) -> None:
        self.chat_log.configure(state=tk.NORMAL)
        self.chat_log.insert(tk.END, f"{role}：{content}\n\n")
        self.chat_log.see(tk.END)
        self.chat_log.configure(state=tk.DISABLED)

    def _set_busy(self, busy: bool, status: str = "") -> None:
        self.sending = busy
        self.send_btn.configure(state=(tk.DISABLED if busy else tk.NORMAL))
        self.quit_btn.configure(state=(tk.DISABLED if busy else tk.NORMAL))
        self.status.configure(text=status)

    def send(self) -> None:
        if self.sending:
            return

        text = self.input_text.get("1.0", tk.END).strip()
        if not text:
            self.status.configure(text="请输入内容。")
            return

        self.input_text.delete("1.0", tk.END)
        self._append("你", text)
        self._set_busy(True, "发送中…")

        threading.Thread(target=self._send_worker, args=(text,), daemon=True).start()

    def _send_worker(self, text: str) -> None:
        try:
            resp = requests.post(
                f"{self.base_url}/chat",
                json={"text": text},
                timeout=120,
            )
            if resp.ok:
                payload = resp.json()
                reply = payload.get("reply", "")
                self.root.after(0, lambda: self._append("Agent", reply))
                self.root.after(0, lambda: self._set_busy(False, "完成。"))
                return

            payload = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            error = payload.get("error") or payload.get("detail") or f"HTTP {resp.status_code}"
            self.root.after(0, lambda: self._set_busy(False, f"错误：{error}"))
        except Exception as exc:
            self.root.after(0, lambda: self._set_busy(False, f"错误：{exc}"))

    def quit(self) -> None:
        # 如果是本进程拉起的 server，直接关窗口即可（daemon 线程会随进程退出）
        if not self.started_server:
            try:
                requests.post(f"{self.base_url}/shutdown", json={}, timeout=3)
            except Exception:
                pass
        self.root.destroy()


def _wait_for_server(base_url: str, timeout_s: float = 6.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            resp = requests.get(f"{base_url}/health", timeout=1.0)
            if resp.ok:
                return True
        except Exception:
            time.sleep(0.2)
    return False


def _start_fastapi_server_in_thread(host: str, port: int) -> None:
    # 通过 import 启动同一进程内的 uvicorn（最少操作、便于桌面一键启动）
    import uvicorn

    from ui.chat_fastapi_server import app

    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    threading.Thread(target=server.run, daemon=True).start()


def _pick_cjk_font_family() -> str | None:
    """Pick a font family that can likely render Chinese characters."""
    try:
        root = tk.Tk()
        root.withdraw()
        families = set(tkfont.families(root))
        root.destroy()
    except Exception:
        return None

    candidates = [
        # Common on Linux
        "Noto Sans CJK SC",
        "Noto Sans CJK",
        "Noto Sans SC",
        "WenQuanYi Micro Hei",
        "WenQuanYi Zen Hei",
        "Source Han Sans SC",
        "AR PL UMing CN",
        # Common on macOS
        "PingFang SC",
        "Hiragino Sans GB",
        # Common on Windows
        "Microsoft YaHei",
        "SimHei",
    ]

    for name in candidates:
        if name in families:
            return name
    return None


def _apply_global_fonts(root: tk.Tk) -> tuple[str, str | None]:
    """Apply a best-effort global font that supports Chinese."""
    chosen = _pick_cjk_font_family()
    warning = None

    if chosen is None:
        # Keep default, but warn: likely missing CJK fonts.
        chosen = tkfont.nametofont("TkDefaultFont").cget("family")
        warning = (
            "未检测到常见中文字体；若中文显示为方块，请安装中文字体包。\n"
            "- Debian/Ubuntu：sudo apt-get install fonts-noto-cjk\n"
            "- Fedora：sudo dnf install google-noto-sans-cjk-fonts"
        )

    # Configure Tk named fonts (affects most widgets)
    for named in ["TkDefaultFont", "TkTextFont", "TkHeadingFont", "TkMenuFont", "TkTooltipFont"]:
        try:
            f = tkfont.nametofont(named)
            f.configure(family=chosen)
        except Exception:
            pass

    # Configure ttk styles (some themes ignore named fonts)
    try:
        style = ttk.Style(root)
        style.configure(".", font=(chosen, 10))
    except Exception:
        pass

    return chosen, warning


def main() -> None:
    host = os.getenv("CHAT_CLIENT_HOST", "127.0.0.1")
    port = int(os.getenv("CHAT_PORT", "8002"))
    base_url = f"http://{host}:{port}"

    start_server = os.getenv("CHAT_START_SERVER", "1").strip().lower() in {"1", "true", "yes"}
    started_server = False

    if start_server:
        _start_fastapi_server_in_thread(host=host, port=port)
        started_server = True

    if not _wait_for_server(base_url, timeout_s=8.0):
        raise RuntimeError(
            f"无法连接到 FastAPI server：{base_url}。"
            "\n你可以：\n- 先运行 `uv run ui/chat_fastapi_server.py` 再启动本窗口\n- 或设置 CHAT_START_SERVER=1 让窗口自动拉起"
        )

    root = tk.Tk()
    ui_font_family, font_warning = _apply_global_fonts(root)
    try:
        ttk.Style().theme_use("clam")
    except Exception:
        pass

    win = ChatWindow(root, base_url=base_url, started_server=started_server, ui_font_family=ui_font_family)
    if font_warning:
        win._append("系统", font_warning)
    root.mainloop()


if __name__ == "__main__":
    main()
