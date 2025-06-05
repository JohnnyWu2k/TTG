"""Entry point for the Pygame 2D version."""

import threading
import time

from network.server import start_server, PORT
from network.client_pygame import run_client


def main():
    # Simple text prompts to start server or join one.
    choice = input("Host (h) or Join (j)? ").strip().lower()
    host = "127.0.0.1"
    if choice == "h":
        print("Starting server...")
        start_server(40, 20)
        time.sleep(0.5)
    elif choice == "j":
        host = input("Server IP: ").strip()

    run_client(host, PORT)


if __name__ == "__main__":
    main()

