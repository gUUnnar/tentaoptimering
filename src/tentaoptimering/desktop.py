"""Windows desktop entry point: serve locally and open the default browser."""

from __future__ import annotations

import threading
import webbrowser

import uvicorn

from .api import create_app


def main() -> int:
    url = "http://127.0.0.1:8765"
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    uvicorn.run(create_app(), host="127.0.0.1", port=8765, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
