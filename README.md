# XP Waste Timer

A RuneScape-themed efficiency timer built with Python and PyQt5 to help you maximize your training gains!

![XP Waste Timer](https://img.shields.io/badge/Python-3.7+-blue.svg)
![RuneScape](https://img.shields.io/badge/Theme-RuneScape-gold.svg)
![Efficiency](https://img.shields.io/badge/XP%20Waste-None-brightgreen.svg)

## ⚡ Features

- ⏰ **Classic Training Method**: 25min focused training, 5min break, 15min long break
- 🎨 **RuneScape Theme**: Beautiful gold and bronze color scheme (plus dark/light modes)  
- 🔔 **Custom Notifications**: Supports .wav, .mp3, and .ogg files (perfect for RuneScape sounds!)
- 📊 **Training History**: Track your completed sessions and total training time
- ⚙️ **Customizable Durations**: Adjust session lengths to fit your training style
- 🎯 **Manual Session Control**: Skip sessions or manually switch between training/breaks
- 💾 **Settings Persistence**: Your preferences are automatically saved

## 🚀 Quick Start

### Easy Setup (Recommended)
1. Run `setup.bat` (installs Python requirements automatically)
2. Double-click `run_xp_waste.pyw` 

### Manual Setup
1. Install Python 3.7+ and pip
2. Double-click `run_xp_waste.pyw`

### Executable Version
1. Run `build_executable.bat` (creates standalone .exe)
2. Find `XPWasteTimer.exe` in the `dist` folder
3. Share with your clan members!

## 🎵 Custom Notification Sounds

Want authentic RuneScape sounds? Check out the [Old School RuneScape Wiki Jingles page](https://oldschool.runescape.wiki/w/Jingles) for various game sounds you can download and use:

- Level up sounds
- Quest completion jingles  
- Skill-specific audio cues
- Combat sounds
- Achievement unlocks

The timer supports .wav, .mp3, and .ogg formats, so you can use any RuneScape audio file!

> **Note**: We don't include copyrighted RuneScape audio files. Please download your own from legitimate sources to avoid copyright issues.

## 💡 How to Train Efficiently

### The XP Waste Prevention Method:
1. **Training Session (25 min)**: Focus intensely on your chosen skill
2. **Quick Break (5 min)**: Rest your hands, check your stats, plan your next moves
3. **Repeat**: After 4 training sessions, take a longer break (15 min)
4. **Long Break (15 min)**: Perfect time for GE runs, bank organization, or just stretching!

### Pro Tips:
- Use for intensive skills like Runecrafting, Agility, or Hunter
- Perfect for maintaining focus during long PvM sessions
- Great for efficient questing and achievement diary completion
- Ideal for maximizing XP/hour on any skill

## 📁 Project Structure

```
xp-waste-timer/
├── main.py                  # Main GUI application  
├── run_xp_waste.pyw         # Main launcher (no console)
├── setup.bat                # One-click dependency installer
├── pomodoro_timer.py        # Core timer logic
├── session_history.py       # Training session tracking
├── build_executable.bat     # Creates standalone .exe
├── requirements.txt         # Python dependencies
└── data/                    # Settings and session history
    ├── settings.json        # User preferences
    └── session_history.json # Training session data
```

## 📸 Screenshots

The timer features three beautiful themes:
- **RuneScape Theme**: Gold text on brown backgrounds with green accents
- **Dark Theme**: Easy on the eyes for late-night grinding sessions  
- **Light Theme**: Great for daytime use

## 🛠️ Features in Detail

### Session Types
- **Training**: Your focused skill grinding time (25 minutes default)
- **Short Break**: Quick rest between training sessions (5 minutes)  
- **Long Break**: Extended rest after completing a cycle (15 minutes)

### Timer Controls
- **Start/Pause**: Control your training session timing
- **Skip**: Jump to the next session type
- **Reset**: Start your current session over
- **Manual Session**: Force switch to Training, Short Break, or Long Break

### Customization Options
- Adjust training session duration (1-60 minutes)
- Modify break lengths to fit your playstyle
- Choose notification sounds (system, custom, or none)
- Select your preferred theme
- Cycle management controls

## 🔧 Requirements

- Python 3.7+
- PyQt5
- PyQt5-multimedia (for custom sounds)

## ⚖️ Legal & Copyright

This timer is inspired by RuneScape but is not affiliated with or endorsed by Jagex Ltd. The "XP Waste" terminology and efficiency focus are common concepts in the RuneScape community.

**Regarding Audio**: This software does not include any copyrighted RuneScape audio files. Users are responsible for obtaining any custom notification sounds legally and ensuring they comply with applicable copyright laws.

## 🤝 Contributing

Feel free to fork this project and make it even better! Some ideas for improvements:

- Additional themes (other games, seasonal themes)  
- Integration with RuneScape hiscores API
- More detailed statistics and goal tracking
- Additional notification options
- Mobile companion app

## 📜 License

This project is open source. Use it to prevent XP waste and achieve maximum gains! 

---

*Stop wasting XP and start training efficiently! 🏆*