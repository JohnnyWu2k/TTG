import curses
import time
from network.server import start_server, PORT
from network.client import run_client

def main_menu(stdscr):
    curses.curs_set(0)
    stdscr.clear()
    # Enable mouse events for the main menu.
    curses.mousemask(curses.ALL_MOUSE_EVENTS)
    
    options = ["Host a game", "Join a game", "Quit"]
    current_selection = 0
    start_y = 3
    start_x = 4
    while True:
        stdscr.clear()
        stdscr.addstr(1, 2, "Welcome to Multiplayer Text RPG", curses.A_BOLD)
        for idx, option in enumerate(options):
            line_y = start_y + idx
            if idx == current_selection:
                line = "--> " + option
            else:
                line = "    " + option
            stdscr.addstr(line_y, start_x, line,
                          curses.A_REVERSE if idx == current_selection else curses.A_NORMAL)
        stdscr.refresh()
        key = stdscr.getch()
        if key == curses.KEY_MOUSE:
            try:
                _, mx, my, _, bstate = curses.getmouse()
                if bstate & curses.BUTTON1_CLICKED:
                    # Check if the click falls within an option row.
                    for idx, option in enumerate(options):
                        if my == start_y + idx and start_x <= mx <= start_x + 20:
                            current_selection = idx
                            return options[current_selection].split()[0].lower()
            except Exception:
                pass
        elif key == curses.KEY_UP and current_selection > 0:
            current_selection -= 1
        elif key == curses.KEY_DOWN and current_selection < len(options) - 1:
            current_selection += 1
        elif key in [curses.KEY_ENTER, 10, 13]:
            return options[current_selection].split()[0].lower()

def get_server_ip(stdscr):
    stdscr.clear()
    stdscr.addstr(2, 2, "Enter server IP (e.g., 127.0.0.1): ")
    stdscr.refresh()
    curses.echo()
    ip = stdscr.getstr(3, 2, 15)
    curses.noecho()
    return ip.decode('utf-8')

def show_progress_bar(stdscr, message="Generating Map...", duration=3):
    stdscr.clear()
    max_y, max_x = stdscr.getmaxyx()
    stdscr.addstr(max_y // 2 - 2, (max_x - len(message)) // 2, message)
    bar_width = max_x - 20
    for i in range(101):
        progress = i / 100.0
        filled = int(bar_width * progress)
        bar = "[" + "#" * filled + "-" * (bar_width - filled) + "]"
        stdscr.addstr(max_y // 2, 10, bar)
        percent_text = f"{i}%"
        stdscr.addstr(max_y // 2 + 1, (max_x - len(percent_text)) // 2, percent_text)
        stdscr.refresh()
        time.sleep(duration / 100.0)
    time.sleep(0.5)

def main(stdscr):
    # Initialize curses colors after initscr() is called.
    curses.start_color()
    curses.use_default_colors()
    # Define a color pair (pair 2: yellow on default background).
    curses.init_pair(2, curses.COLOR_YELLOW, -1)
    
    mode = main_menu(stdscr)
    if mode == "quit":
        return

    server_host = "127.0.0.1"
    if mode == "host":
        max_y, max_x = stdscr.getmaxyx()
        start_server(max_x, max_y)
        server_host = "127.0.0.1"
        show_progress_bar(stdscr, message="Generating Map...", duration=3)
    elif mode == "join":
        server_host = get_server_ip(stdscr)
    
    run_client(stdscr, server_host, PORT)

if __name__ == "__main__":
    curses.wrapper(main)
