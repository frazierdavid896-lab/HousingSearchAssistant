from __future__ import annotations

import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

from streamlit.web import cli as stcli


def bundled_path(filename: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / filename


def find_free_port(start: int = 8501, end: int = 8599) -> int:
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("No available local port was found.")


def open_browser_when_ready(url: str) -> None:
    time.sleep(2.5)
    webbrowser.open(url)


def main() -> None:
    app_path = bundled_path("app.py")
    port = find_free_port()
    url = f"http://127.0.0.1:{port}"

    threading.Thread(
        target=open_browser_when_ready,
        args=(url,),
        daemon=True,
    ).start()

    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--server.address=127.0.0.1",
        f"--server.port={port}",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
        "--global.developmentMode=false",
    ]

    raise SystemExit(stcli.main())


if __name__ == "__main__":
    main()
