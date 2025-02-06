# main.py
import curses
from network.server import start_server, PORT
from network.client import run_client

def main_menu(stdscr):
    curses.curs_set(0)
    stdscr.clear()
    stdscr.addstr(2, 2, "Welcome to Multiplayer Text RPG")
    stdscr.addstr(4, 2, "Press H to Host a game")
    stdscr.addstr(5, 2, "Press J to Join a game")
    stdscr.addstr(6, 2, "Press Q to Quit")
    stdscr.refresh()
    while True:
        key = stdscr.getch()
        if key in [ord('h'), ord('H')]:
            return "host"
        elif key in [ord('j'), ord('J')]:
            return "join"
        elif key in [ord('q'), ord('Q')]:
            return "quit"

def get_server_ip(stdscr):
    stdscr.clear()
    stdscr.addstr(2, 2, "Enter server IP (e.g., 127.0.0.1): ")
    stdscr.refresh()
    curses.echo()
    ip = stdscr.getstr(3, 2, 15)
    curses.noecho()
    return ip.decode('utf-8')

def main(stdscr):
    mode = main_menu(stdscr)
    if mode == "quit":
        return
    server_host = "127.0.0.1"
    if mode == "host":
        start_server()
        server_host = "127.0.0.1"
    elif mode == "join":
        server_host = get_server_ip(stdscr)
    run_client(stdscr, server_host, PORT)

if __name__ == "__main__":
    curses.wrapper(main)
