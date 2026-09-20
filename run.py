"""Start the local website and automatic background jobs in one process."""

import threading
from waitress import serve
from app import create_app
from app.automation import loop

app = create_app()
if __name__ == "__main__":
    stop = threading.Event()
    threading.Thread(target=loop, args=(app, stop), daemon=True).start()
    print(
        "\nNowshera Family Clinic: http://127.0.0.1:5000\nKeep this window open. Press Ctrl+C to stop.\n",
        flush=True,
    )
    try:
        serve(app, host="127.0.0.1", port=5000, threads=6)
    finally:
        stop.set()
