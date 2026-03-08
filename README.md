# XP Waste - Pomodoro Timer

XP Waste is a desktop focus timer for RuneScape players.
It uses a Pomodoro-style cycle to help you train consistently and avoid idle downtime.

<p>
  <img width="49%" src="https://github.com/user-attachments/assets/e71c30dd-0d49-459b-8f46-d249c16a5c4b" />
  <img width="49%" src="https://github.com/user-attachments/assets/3a77f6f6-e0c6-42a7-b1a7-5516c5276a58" />
</p>

## Quick Start (Windows)

Most users can start the app by running the executable directly:

1. Download or open the project folder.
2. Double-click `XPWaste.exe`.

No Python installation is required to run the `.exe`.

### Windows Security Warning

Because this is an unsigned executable, Windows SmartScreen may show a warning such as
"Windows protected your PC."

If you trust the file source, click:

1. `More info`
2. `Run anyway`

## Features

- OSRS mode and Normal mode themes
- Configurable focus, short break, long break, and cycle length
- Manual session controls (Focus, Short Break, Long Break)
- Optional custom notification sounds (`.wav`, `.mp3`, `.ogg`, `.m4a`)
- Stopwatch-style active study tracking (second-accurate)
- Session history with daily and overall totals based on active study time
- Windows standalone executable support via PyInstaller

## Default Timer Values

- Focus: `25` minutes
- Short break: `5` minutes
- Long break: `15` minutes
- Long break every: `4` focus sessions

## Project Structure

```text
xpwaste/
├── source/                 # Main app source code
├── assets/                 # App icon and assets
├── data/                   # Runtime settings and session history
├── build-tools/            # Build scripts and PyInstaller spec
├── XPWaste.exe             # Built Windows executable (optional in repo)
└── README.md
```

## Run From Source

1. Install Python 3.11+.
2. Install dependencies:
	- `pip install -r build-tools/requirements.txt`
3. Start the app:
	- `python source/main.py`

## Build Executable

From `build-tools/`:

- `build_executable.bat`

Or direct command:

- `python -m PyInstaller --onefile --windowed --distpath "..\\dist" --workpath "..\\build" --add-data "..\\data;data" --add-data "..\\assets;assets" --icon "..\\assets\\xpwaste.ico" --name "XPWaste" --clean "..\\source\\main.py"`

## Notes

- Runtime files in `data/` are user-specific and should not be committed.
- Study tracking counts only active timer runtime; paused time is excluded.
- Skipping a focus session still records elapsed active study time when at least 60 seconds were completed.
- Sound effects are not bundled with this project due to copyright/licensing reasons.
- If you want Old School RuneScape-style jingles, download them yourself from:
	`https://oldschool.runescape.wiki/w/Jingles`
- XP Waste is a fan-made personal project built for fun.
- This project is not affiliated with, endorsed by, sponsored by, or connected to Jagex Ltd.
- RuneScape and Old School RuneScape are trademarks of Jagex Ltd.
