"""Local entry point. Waitress also works on Windows."""

import os

from dotenv import load_dotenv
from waitress import serve

from campusfind import create_app

load_dotenv()
app = create_app()

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5000"))
    print(f"CampusFind is running at http://{host}:{port}", flush=True)
    try:
        serve(app, host=host, port=port, threads=4)
    except KeyboardInterrupt:
        print("\nCampusFind stopped.")
