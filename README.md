# TTG

[Download from here](https://github.com/JohnnyWu2k/TTG/releases)

## Setup

1. Install **Python 3.12** or newer.
2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Game

Start both the server and client with a single command:

```bash
python main.py
```

You will be prompted to either **host** a game (starts a local server on port 12345) or **join** by entering the host's IP address.

## Controls

- **W/A/S/D** &ndash; move your character
- **X** &ndash; attack a nearby enemy (opens a combat minigame)
- **B** &ndash; toggle building mode (click to place from the selected slot)
- **P** &ndash; open the shop to buy building blocks
- **1&ndash;5** &ndash; select inventory slot
- **Mouse wheel** &ndash; zoom in/out
- **Esc** &ndash; pause menu

## Gameplay Overview

TTG is a multiplayer text RPG rendered in the terminal using `curses`. The world is procedurally generated and shared between connected players. Host a session so others can join, explore the map, build structures and fight enemies together.
