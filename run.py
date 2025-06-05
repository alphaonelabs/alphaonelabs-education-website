import os
import signal
import sys
from pathlib import Path

import django
import uvicorn

# Add the project root directory to Python path
root_dir = Path(__file__).resolve().parent
sys.path.append(str(root_dir))

# Set up Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.settings")

# Set up Django application
django.setup()


def signal_handler(sig, frame):
    print("\nShutting down server...")
    sys.exit(0)


if __name__ == "__main__":
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)

    # Configure and run server
    config = uvicorn.Config(
        "web.asgi:application",
        host="127.0.0.1",
        port=8001,
        reload=True,
        reload_dirs=[str(root_dir)],
        log_level="info",
        ws_ping_interval=20,  # Send ping frames every 20 seconds
        ws_ping_timeout=30,  # Wait 30 seconds for pong response
        timeout_keep_alive=30,  # Close idle connections after 30 seconds
    )
    server = uvicorn.Server(config)
    server.run()
