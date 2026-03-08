# XP Waste

XP Waste is a desktop focus timer for RuneScape players.
It uses a Pomodoro-style cycle to help you train consistently and avoid idle downtime.

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
- Session history with daily and overall totals
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
- This project is not affiliated with Jagex Ltd.