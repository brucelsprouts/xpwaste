import sys
import json
import os
from datetime import datetime

from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen, QIcon
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QGroupBox,
    QFormLayout,
    QSpinBox,
    QDialog,
    QDialogButtonBox,
    QMessageBox,
    QFrame,
    QComboBox,
    QCheckBox,
    QFileDialog,
    QListView,
)

from xp_waste_timer import XPWasteTimer
from session_history import SessionHistoryManager


def _resource_path(relative_path):
    """Return absolute path for dev and PyInstaller onefile contexts."""
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        # In source mode, resolve resources relative to project root
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base_path, relative_path)


def _app_root_path():
    """Return stable writable app root for both source and frozen runs."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class XPWasteWindow(QMainWindow):
    """
    Main application window that connects the XP Waste logic to the UI.
    Handles start/pause/reset controls, history display, total study time,
    simple notifications, and optional duration customization.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("XP Waste")

        self._app_root = _app_root_path()
        self._data_dir = os.path.join(self._app_root, "data")

        icon_path = _resource_path(os.path.join("assets", "xpwaste.ico"))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Core logic objects
        self.timer = XPWasteTimer(self)
        history_file = os.path.join(self._data_dir, "session_history.json")
        self.history_manager = SessionHistoryManager(history_file=history_file)
        self._last_session_type = self.timer.current_session_type
        self._theme = "runescape"  # Default to RuneScape theme
        
        # Settings file path
        self._settings_file = os.path.join(self._data_dir, "settings.json")
        
        # Notification settings (load from file)
        self._load_settings()
        self._media_player = QMediaPlayer()

        # Build UI and connect logic
        self._build_ui()
        self._connect_signals()
        self._load_existing_history()
        self._update_total_time_label()
        
    def _load_settings(self):
        """Load settings from file."""
        # Default settings
        self._notification_sound = "system" 
        self._custom_sound_file = None
        self._skip_increments_cycle = False
        self._minimum_log_seconds = 60
        self._theme = "runescape"
        focus_time = self.timer.FOCUS_TIME
        short_break_time = self.timer.SHORT_BREAK_TIME
        long_break_time = self.timer.LONG_BREAK_TIME
        cycle_length = self.timer.FOCUS_SESSIONS_BEFORE_LONG_BREAK
        
        try:
            if os.path.exists(self._settings_file):
                with open(self._settings_file, 'r') as f:
                    settings = json.load(f)
                    self._notification_sound = settings.get("notification_sound", "system")
                    self._custom_sound_file = settings.get("custom_sound_file", None)
                    self._skip_increments_cycle = settings.get("skip_increments_cycle", False)
                    self._minimum_log_seconds = max(0, int(settings.get("minimum_log_seconds", 60)))
                    loaded_theme = settings.get("theme", "runescape")
                    if loaded_theme in ("runescape", "dark"):
                        self._theme = loaded_theme

                    # Load timer settings and apply to current countdown
                    focus_time = settings.get("focus_time", focus_time)
                    short_break_time = settings.get("short_break_time", short_break_time)
                    long_break_time = settings.get("long_break_time", long_break_time)
                    cycle_length = settings.get("cycle_length", cycle_length)

            self.timer.set_durations(focus_time, short_break_time, long_break_time, reset_current=True)
            self.timer.set_cycle_length(cycle_length)
            self.timer.set_minimum_log_seconds(self._minimum_log_seconds)
        except Exception as e:
            print(f"Failed to load settings: {e}")
            
    def _save_settings(self):
        """Save settings to file."""
        try:
            os.makedirs(os.path.dirname(self._settings_file), exist_ok=True)
            settings = {
                "notification_sound": self._notification_sound,
                "custom_sound_file": self._custom_sound_file,
                "skip_increments_cycle": self._skip_increments_cycle,
                "minimum_log_seconds": self._minimum_log_seconds,
                "theme": self._theme,
                "focus_time": self.timer.FOCUS_TIME,
                "short_break_time": self.timer.SHORT_BREAK_TIME,
                "long_break_time": self.timer.LONG_BREAK_TIME,
                "cycle_length": self.timer.FOCUS_SESSIONS_BEFORE_LONG_BREAK
            }
            with open(self._settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"Failed to save settings: {e}")

    def _build_ui(self):
        """Creates and arranges all UI widgets."""
        central_widget = QWidget()
        central_widget.setObjectName("RootWidget")
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Menu bar / settings
        menu_bar = self.menuBar()
        settings_menu = menu_bar.addMenu("&Settings")
        durations_action = settings_menu.addAction("Timer Durations...")
        durations_action.triggered.connect(self._open_duration_settings)
        settings_menu.addSeparator()
        about_action = settings_menu.addAction("About XP Waste...")
        about_action.triggered.connect(self._show_about_dialog)

        # Title
        title_label = QLabel("XP Waste")
        title_label.setObjectName("TitleLabel")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # Manual session selection (moved to top)
        session_controls_layout = QHBoxLayout()
        self.focus_session_button = QPushButton("Focus")
        self.short_break_button = QPushButton("Short Break")
        self.long_break_button = QPushButton("Long Break")
        session_controls_layout.addWidget(self.focus_session_button)
        session_controls_layout.addWidget(self.short_break_button)
        session_controls_layout.addWidget(self.long_break_button)
        main_layout.addLayout(session_controls_layout)

        # Session / timer box
        self.session_box = QFrame()
        self.session_box.setObjectName("SessionBox")
        session_box_layout = QVBoxLayout()
        self.session_box.setLayout(session_box_layout)

        # Session type label (moved inside color box)
        self.session_label = QLabel(f"{self.timer.current_session_type} Session")
        self.session_label.setObjectName("SessionLabel")
        self.session_label.setAlignment(Qt.AlignCenter)
        session_box_layout.addWidget(self.session_label)

        # Countdown label
        self.time_label = QLabel(self._format_time(self.timer.time_remaining))
        self.time_label.setObjectName("TimeLabel")
        self.time_label.setAlignment(Qt.AlignCenter)
        session_box_layout.addWidget(self.time_label)

        # Cycle info label with inline controls
        cycle_layout = QHBoxLayout()
        cycle_layout.setAlignment(Qt.AlignCenter)
        self.cycle_minus_button = QPushButton("−")
        self.cycle_minus_button.setFlat(True)
        self.cycle_minus_button.setFixedSize(20, 20)
        self.cycle_minus_button.setStyleSheet("QPushButton { border: none; background: transparent; font-size: 16px; padding: 0; }")
        self.cycle_label = QLabel("")
        self.cycle_label.setObjectName("CycleLabel")
        self.cycle_label.setAlignment(Qt.AlignCenter)
        self.cycle_plus_button = QPushButton("+")
        self.cycle_plus_button.setFlat(True)
        self.cycle_plus_button.setFixedSize(20, 20)
        self.cycle_plus_button.setStyleSheet("QPushButton { border: none; background: transparent; font-size: 16px; padding: 0; }")
        cycle_layout.addWidget(self.cycle_minus_button)
        cycle_layout.addWidget(self.cycle_label)
        cycle_layout.addWidget(self.cycle_plus_button)
        session_box_layout.addLayout(cycle_layout)

        main_layout.addWidget(self.session_box)

        # Control buttons
        controls_layout = QHBoxLayout()
        self.start_pause_button = QPushButton("Start")
        self.skip_button = QPushButton("Skip")
        self.reset_button = QPushButton("Reset")
        controls_layout.addWidget(self.start_pause_button)
        controls_layout.addWidget(self.skip_button)
        controls_layout.addWidget(self.reset_button)
        main_layout.addLayout(controls_layout)

        # Total / overall study time labels (swapped order - overall first)
        time_totals_layout = QHBoxLayout()
        self.overall_time_label = QLabel("")
        self.overall_time_label.setObjectName("OverallTimeLabel")
        self.total_time_label = QLabel("")
        self.total_time_label.setObjectName("TotalTimeLabel")
        time_totals_layout.addWidget(self.overall_time_label)
        time_totals_layout.addWidget(self.total_time_label)
        main_layout.addLayout(time_totals_layout)

        # History list
        history_group = QGroupBox("History")
        history_group.setObjectName("HistoryGroup")
        history_layout = QVBoxLayout()
        history_group.setLayout(history_layout)

        self.history_list = QListWidget()
        history_layout.addWidget(self.history_list)

        main_layout.addWidget(history_group)

        # Apply RuneScape theme styling
        self._apply_theme()
        # Initialize derived labels
        self._update_cycle_label()

    def _connect_signals(self):
        """Connects timer signals and button clicks to handlers."""
        # Buttons
        self.start_pause_button.clicked.connect(self._handle_start_pause_toggle)
        self.skip_button.clicked.connect(self._handle_skip)
        self.reset_button.clicked.connect(self._handle_reset)
        self.focus_session_button.clicked.connect(lambda: self._handle_force_session("Focus"))
        self.short_break_button.clicked.connect(lambda: self._handle_force_session("Short Break"))
        self.long_break_button.clicked.connect(lambda: self._handle_force_session("Long Break"))
        self.cycle_minus_button.clicked.connect(self._handle_cycle_decrement)
        self.cycle_plus_button.clicked.connect(self._handle_cycle_increment)

        # Timer signals
        self.timer.countdown_updated.connect(self._on_countdown_updated)
        self.timer.session_changed.connect(self._on_session_changed)
        self.timer.focus_session_completed.connect(self._on_focus_session_completed)

        # Sync initial state
        self._update_start_pause_button()

    def _load_existing_history(self):
        """Loads previously saved sessions into the history list."""
        self._refresh_history_list()

    def _apply_theme(self):
        """Applies the current theme (runescape or normal) to the whole window."""
        if self._theme == "runescape":
            # Dark-base RuneScape palette (subtle accents)
            style = """
            QWidget {
                color: #e6dcc8;
                font-family: Segoe UI, sans-serif;
                background-color: #121212;
            }
            QDialog {
                background-color: #121212;
            }
            QMenuBar {
                background-color: #121212;
                color: #e6dcc8;
                border: none;
            }
            QMenuBar::item:selected {
                background-color: #1f1f1f;
            }
            QMenu {
                background-color: #161616;
                color: #e6dcc8;
                border: 1px solid #3a3125;
            }
            QMenu::item:selected {
                background-color: #3b2f1f;
                color: #ffcf3f;
            }
            #SessionBox {
                border-radius: 8px;
                padding: 8px;
                border: 1px solid #3a3125;
            }
            #SessionBox[sessionType="focus"] {
                background-color: #1d1a16;
                border-color: #694d23;
            }
            #SessionBox[sessionType="short_break"] {
                background-color: #1a2b23;
                border-color: #3f6b52;
            }
            #SessionBox[sessionType="long_break"] {
                background-color: #1b2633;
                border-color: #3f6487;
            }
            #TitleLabel {
                font-size: 24px;
                margin: 12px 0;
                color: #e6a519;
            }
            #SessionLabel {
                font-size: 18px;
                margin: 8px 0;
                color: #d8c7a4;
            }
            #CycleLabel {
                font-size: 13px;
                margin: 4px 0;
                color: #bfa67a;
            }
            #TimeLabel {
                font-size: 40px;
                margin: 16px 0;
                color: #ffcf3f;
            }
            #SessionLabel, #TimeLabel, #CycleLabel {
                background-color: transparent;
            }
            #TotalTimeLabel, #OverallTimeLabel {
                font-size: 14px;
                margin: 4px 0;
                color: #cdbb97;
            }
            QPushButton {
                background-color: #2b251b;
                color: #dfd2b8;
                border: 1px solid #4a3a24;
                border-radius: 4px;
                padding: 6px 14px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #342d21;
                border-color: #694d23;
            }
            QPushButton:pressed {
                background-color: #1f1b14;
                color: #e6a519;
            }
            QGroupBox {
                border: 1px solid #3a3125;
                border-radius: 4px;
                margin-top: 10px;
                color: #cfbe9b;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            QListWidget {
                background-color: #181818;
                border: 1px solid #3a3125;
                color: #d8ccb2;
                outline: 0;
            }
            QListWidget::item:selected {
                background-color: #2b2218;
                color: #e6a519;
            }
            QListWidget::item:focus {
                outline: none;
            }
            QSpinBox {
                background-color: #1a1a1a;
                color: #d8ccb2;
                border: 1px solid #3a3125;
                border-radius: 4px;
                padding: 4px 8px;
                min-height: 20px;
            }
            QSpinBox::up-button,
            QSpinBox::down-button {
                width: 0px;
                border: none;
            }
            QSpinBox::up-arrow,
            QSpinBox::down-arrow {
                image: none;
                width: 0px;
                height: 0px;
            }
            QComboBox {
                background-color: #1a1a1a;
                color: #d8ccb2;
                border: 1px solid #3a3125;
                border-radius: 4px;
                padding: 4px 8px;
                min-height: 20px;
            }
            QComboBox:hover {
                border-color: #694d23;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid #3a3125;
                background-color: #2b251b;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0px;
                height: 0px;
            }
            QComboBox QAbstractItemView {
                background-color: #161616;
                color: #d8ccb2;
                border: 1px solid #3a3125;
                selection-background-color: #2b2218;
                selection-color: #e6a519;
            }
            QCheckBox {
                color: #d8ccb2;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid #3a3125;
                border-radius: 2px;
                background-color: #1a1a1a;
            }
            QCheckBox::indicator:checked {
                background-color: #694d23;
                border-color: #8a6a3a;
            }
            QCheckBox::indicator:hover {
                border-color: #694d23;
            }
            QScrollBar:vertical {
                background-color: transparent;
                width: 8px;
                border: none;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background-color: #4a3a24;
                border-radius: 4px;
                min-height: 20px;
                margin: 0;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #5b472c;
            }
            QScrollBar:horizontal {
                background-color: transparent;
                height: 8px;
                border: none;
                margin: 0;
            }
            QScrollBar::handle:horizontal {
                background-color: #4a3a24;
                border-radius: 4px;
                min-width: 20px;
                margin: 0;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #5b472c;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical,
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {
                width: 0px;
                height: 0px;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical,
            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {
                background: transparent;
            }
            """
        else:
            style = """
            QWidget {
                color: #f0f0f0;
                font-family: Segoe UI, sans-serif;
                background-color: #121212;
            }
            QDialog {
                background-color: #121212;
            }
            QMenuBar {
                background-color: #121212;
                color: #f0f0f0;
                border: none;
            }
            QMenuBar::item:selected {
                background-color: #1e1e1e;
            }
            QMenu {
                background-color: #121212;
                color: #f0f0f0;
                border: 1px solid #333333;
            }
            QMenu::item:selected {
                background-color: #1e88e5;
            }
            #SessionBox {
                border-radius: 8px;
                padding: 8px;
                border: 1px solid #333333;
            }
            #SessionBox[sessionType="focus"] {
                background-color: #1e1e1e;
            }
            #SessionBox[sessionType="short_break"] {
                background-color: #102a43;
            }
            #SessionBox[sessionType="long_break"] {
                background-color: #133321;
            }
            #TitleLabel {
                font-size: 24px;
                margin: 12px 0;
            }
            #SessionLabel {
                font-size: 18px;
                margin: 8px 0;
            }
            #CycleLabel {
                font-size: 13px;
                margin: 4px 0;
            }
            #TimeLabel {
                font-size: 40px;
                margin: 16px 0;
            }
            #SessionLabel, #TimeLabel, #CycleLabel {
                background-color: transparent;
            }
            #TotalTimeLabel, #OverallTimeLabel {
                font-size: 14px;
                margin: 4px 0;
            }
            QPushButton {
                background-color: #2d2d2d;
                color: #f0f0f0;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 6px 14px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
            }
            QPushButton:pressed {
                background-color: #222222;
            }
            QGroupBox {
                border: 1px solid #333333;
                border-radius: 4px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            QListWidget {
                background-color: #1e1e1e;
                border: 1px solid #333333;
                outline: 0;
            }
            QListWidget::item:selected {
                background-color: #3a3a3a;
                color: #ffffff;
            }
            QListWidget::item:focus {
                outline: none;
            }
            QSpinBox {
                background-color: #1e1e1e;
                color: #f0f0f0;
                border: 1px solid #333333;
                border-radius: 4px;
                padding: 4px 8px;
                min-height: 20px;
            }
            QSpinBox::up-button {
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 18px;
                border-left: 1px solid #333333;
                border-bottom: 1px solid #333333;
                border-top-right-radius: 4px;
                background-color: #2d2d2d;
            }
            QSpinBox::up-button:hover {
                background-color: #3a3a3a;
            }
            QSpinBox::up-button:pressed {
                background-color: #222222;
            }
            QSpinBox::down-button {
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 18px;
                border-left: 1px solid #333333;
                border-top: 1px solid #333333;
                border-bottom-right-radius: 4px;
                background-color: #2d2d2d;
            }
            QSpinBox::down-button:hover {
                background-color: #3a3a3a;
            }
            QSpinBox::down-button:pressed {
                background-color: #222222;
            }
            QSpinBox::up-button,
            QSpinBox::down-button {
                width: 0px;
                border: none;
            }
            QSpinBox::up-arrow,
            QSpinBox::down-arrow {
                image: none;
                width: 0px;
                height: 0px;
            }
            QComboBox {
                background-color: #1e1e1e;
                color: #f0f0f0;
                border: 1px solid #333333;
                border-radius: 4px;
                padding: 4px 8px;
                min-height: 20px;
            }
            QComboBox:hover {
                border-color: #555555;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid #333333;
                background-color: #2d2d2d;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0px;
                height: 0px;
            }
            QComboBox QAbstractItemView {
                background-color: #1e1e1e;
                color: #f0f0f0;
                border: 1px solid #333333;
                selection-background-color: #3a3a3a;
                selection-color: #ffffff;
            }
            QCheckBox {
                color: #f0f0f0;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid #444444;
                border-radius: 2px;
                background-color: #1e1e1e;
            }
            QCheckBox::indicator:checked {
                background-color: #4a7a4a;
                border-color: #6aa06a;
            }
            QCheckBox::indicator:hover {
                border-color: #666666;
            }
            QScrollBar:vertical {
                background-color: transparent;
                width: 8px;
                border: none;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background-color: #505050;
                border-radius: 4px;
                min-height: 20px;
                margin: 0;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #606060;
            }
            QScrollBar::handle:vertical:pressed {
                background-color: #404040;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
                width: 0px;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
            }
            QScrollBar:horizontal {
                background-color: transparent;
                height: 8px;
                border: none;
                margin: 0;
            }
            QScrollBar::handle:horizontal {
                background-color: #505050;
                border-radius: 4px;
                min-width: 20px;
                margin: 0;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #606060;
            }
            QScrollBar::handle:horizontal:pressed {
                background-color: #404040;
            }
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {
                width: 0px;
                height: 0px;
            }
            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {
                background: transparent;
            }
            """

        self.setStyleSheet(style)
        # Set initial session background state
        self._update_session_background(self.timer.current_session_type)

    def _set_theme(self, theme: str):
        """Updates the current theme and reapplies styles."""
        if theme not in ("runescape", "dark"):
            return
        self._theme = theme
        self._apply_theme()
        self._refresh_history_list()

    def _play_notification_sound(self):
        """Plays the configured notification sound."""
        if self._notification_sound == "system":
            QApplication.beep()
        elif self._notification_sound == "custom" and self._custom_sound_file:
            try:
                url = QUrl.fromLocalFile(self._custom_sound_file)
                content = QMediaContent(url)
                self._media_player.setMedia(content)
                self._media_player.play()
            except Exception as e:
                print(f"Failed to play custom sound: {e}")
                # Fallback to system beep if custom sound fails
                QApplication.beep()
        # "none" option plays no sound

    def _show_about_dialog(self):
        """Shows information about XP Waste prevention and efficient training."""
        about_text = """
<h2>About XP Waste</h2>

<p>XP Waste is a focused session timer for RuneScape players, built around a Pomodoro-style loop.
It helps you stay consistent, track progress, and reduce downtime between training sessions.</p>

<h3>Default Timer Flow</h3>
<ol>
<li><strong>Focus:</strong> 25 minutes</li>
<li><strong>Short Break:</strong> 5 minutes</li>
<li><strong>Long Break:</strong> 15 minutes every 4 focus sessions</li>
</ol>

<h3>Features</h3>
<ul>
<li>OSRS-inspired theme and a clean normal theme</li>
<li>Custom timer durations and cycle length</li>
<li>Timer Settings include color mode selection and minimum history log seconds</li>
<li>Custom notification sounds (wav, mp3, ogg, m4a)</li>
<li>Session history with second-accurate active study tracking</li>
<li>Manual focus/break switching and cycle progress controls</li>
</ul>

<p><em>Tip: By default, skipping a focus session does not advance the cycle.
You can enable skip-to-increment behavior in Timer Settings. Active study time
counts only while the timer is running, so paused time is not included. Use
minimum history log seconds to avoid tiny history entries.</em></p>
        """
        
        msg = QMessageBox(self)
        msg.setWindowTitle("About XP Waste")
        msg.setTextFormat(Qt.RichText)
        msg.setText(about_text)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    # ------------------------------------------------------------------ #
    # Button handlers
    # ------------------------------------------------------------------ #
    def _handle_start_pause_toggle(self):
        """Toggles timer running state and button text."""
        if self.timer.is_running:
            self.timer.pause()
        else:
            self.timer.start()
        self._update_start_pause_button()

    def _update_start_pause_button(self):
        """Shows Pause while running, otherwise Start."""
        if getattr(self.timer, "is_running", False):
            self.start_pause_button.setText("Pause")
        else:
            self.start_pause_button.setText("Start")

    def _handle_reset(self):
        self.timer.reset()
        self._update_start_pause_button()

    def _handle_skip(self):
        if self._skip_increments_cycle and self.timer.current_session_type == "Focus":
            # Skip but still increment cycle count
            self.timer.skip_current_session_with_increment()
        else:
            # Skip without incrementing cycle (default behavior)
            self.timer.skip_current_session()
        self._update_cycle_label()
        self._update_start_pause_button()

    def _handle_force_session(self, session_type: str):
        """Manually switches to a specific session type."""
        self.timer.force_session_type(session_type)
        self._update_cycle_label()
        self._update_start_pause_button()

    def _handle_cycle_increment(self):
        """Increment the current cycle count."""
        self.timer.increment_cycle_count()
        self._update_cycle_label()

    def _handle_cycle_decrement(self):
        """Decrement the current cycle count."""
        self.timer.decrement_cycle_count()
        self._update_cycle_label()

    def _open_duration_settings(self):
        dialog = DurationSettingsDialog(
            focus_minutes=self.timer.FOCUS_TIME,
            short_break_minutes=self.timer.SHORT_BREAK_TIME,
            long_break_minutes=self.timer.LONG_BREAK_TIME,
            cycle_length=self.timer.focus_sessions_per_cycle,
            notification_sound=self._notification_sound,
            custom_sound_file=self._custom_sound_file,
            skip_increments_cycle=self._skip_increments_cycle,
            minimum_log_seconds=self._minimum_log_seconds,
            current_theme=self._theme,
            parent=self,
        )
        if dialog.exec_() == QDialog.Accepted:
            focus, short_break, long_break, cycle_length, sound_setting, sound_file, skip_behavior, min_log_seconds, selected_theme = dialog.get_values()
            self.timer.set_durations(focus, short_break, long_break, reset_current=True)
            self.timer.set_cycle_length(cycle_length)
            self.timer.set_minimum_log_seconds(min_log_seconds)
            self._notification_sound = sound_setting
            self._custom_sound_file = sound_file
            self._skip_increments_cycle = skip_behavior
            self._minimum_log_seconds = min_log_seconds
            self._set_theme(selected_theme)
            self._save_settings()  # Save settings to file
            self._update_cycle_label()

    # ------------------------------------------------------------------ #
    # Timer signal handlers
    # ------------------------------------------------------------------ #
    def _on_countdown_updated(self, remaining_seconds):
        self.time_label.setText(self._format_time(remaining_seconds))

    def _on_session_changed(self, session_type):
        # Play notification sound
        self._play_notification_sound()

        # Pause timer so user must manually start next session
        self.timer.pause()
        
        self.session_label.setText(f"{session_type} Session")
        self._update_session_background(session_type)
        self._update_cycle_label()
        self._last_session_type = session_type
        self._update_start_pause_button()

    def _on_focus_session_completed(self, start_iso, end_iso, duration_seconds):
        """
        Stores a completed focus session in history and updates the UI.
        duration_seconds is converted to minutes for storage and totals.
        """
        try:
            start_dt = datetime.fromisoformat(start_iso)
            end_dt = datetime.fromisoformat(end_iso)
        except ValueError:
            # Fallback if parsing fails for any reason
            start_dt = datetime.now()
            end_dt = datetime.now()

        date_str = start_dt.strftime("%Y-%m-%d")
        start_str = start_dt.strftime("%H:%M")
        end_str = end_dt.strftime("%H:%M")
        active_seconds = max(0, int(duration_seconds))
        if active_seconds <= 0:
            return
        duration_minutes = active_seconds // 60

        session_data = {
            "date": date_str,
            "start_time": start_str,
            "end_time": end_str,
            "duration": duration_minutes,
            "active_seconds": active_seconds,
            "session_type": "Focus",
        }

        self.history_manager.add_session(session_data)
        self._add_history_item_to_list(session_data)
        self._update_total_time_label()
        self._update_cycle_label()

    # ------------------------------------------------------------------ #
    # History helpers
    # ------------------------------------------------------------------ #
    def _add_history_item_to_list(self, session):
        """
        Adds a single session entry to the history list widget at the top.

        Expected keys in `session`:
            - date (str)
            - start_time (str)
            - end_time (str)
            - duration (int, minutes)
        """
        text = self._format_history_item_text(session)
        item = QListWidgetItem(text)
        self.history_list.insertItem(0, item)  # Insert at top instead of bottom

    def _refresh_history_list(self):
        """Reloads history list text."""
        self.history_list.clear()
        for session in self.history_manager.get_history():
            self._add_history_item_to_list(session)

    def _format_history_item_text(self, session):
        """Returns display text for a history row."""
        date = session.get("date", "")
        start_time = session.get("start_time", "")
        end_time = session.get("end_time", "")
        seconds = session.get("active_seconds")
        if seconds is None:
            seconds = int(session.get("duration", 0)) * 60
        return f"{date}  {start_time} - {end_time}  ({self._format_duration(int(seconds))})"

    def _update_total_time_label(self):
        total_seconds = self.history_manager.get_total_study_seconds_today()
        self.total_time_label.setText(f"Today's Focus Time: {self._format_duration(total_seconds)}")
        overall_seconds = self.history_manager.get_total_study_seconds_overall()
        self.overall_time_label.setText(f"Overall Focus Time: {self._format_duration(overall_seconds)}")
        self._update_cycle_label()

    def _update_cycle_label(self):
        """Updates the label showing the current cycle progress."""
        try:
            completed = self.timer.focus_sessions_completed
            per_cycle = self.timer.focus_sessions_per_cycle
        except AttributeError:
            self.cycle_label.setText("")
            return

        # When in a focus session, show the upcoming number in the cycle.
        if self.timer.current_session_type == "Focus":
            current_number = completed + 1
        else:
            current_number = completed

        # Clamp to at least 0 and not above per_cycle
        current_number = max(0, min(current_number, per_cycle))

        self.cycle_label.setText(f"Cycle: {current_number} / {per_cycle}")

    # ------------------------------------------------------------------ #
    # Utility
    # ------------------------------------------------------------------ #
    @staticmethod
    def _format_time(total_seconds):
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    @staticmethod
    def _format_duration(total_seconds):
        """Formats elapsed seconds as a compact h/m/s label."""
        total_seconds = max(0, int(total_seconds))
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        return f"{minutes}m {seconds}s"

    def _update_session_background(self, session_type):
        """Updates the root widget background color based on the session type."""
        box = getattr(self, "session_box", None)
        if not box:
            return
        if session_type == "Focus":
            box.setProperty("sessionType", "focus")
        elif session_type == "Short Break":
            box.setProperty("sessionType", "short_break")
        elif session_type == "Long Break":
            box.setProperty("sessionType", "long_break")
        # Re-apply style for dynamic property change to take effect
        box.style().unpolish(box)
        box.style().polish(box)
        box.update()


class DurationSettingsDialog(QDialog):
    """Dialog window for adjusting XP Waste durations and cycle length."""

    def __init__(self, focus_minutes, short_break_minutes, long_break_minutes, cycle_length, 
                 notification_sound="system", custom_sound_file=None, skip_increments_cycle=False,
                 minimum_log_seconds=60, current_theme="runescape", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Timer Settings")
        # Remove the question mark help button
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # Duration settings
        self.focus_spin = QSpinBox()
        self.focus_spin.setRange(1, 240)
        self.focus_spin.setValue(focus_minutes)
        self.focus_spin.setButtonSymbols(QSpinBox.NoButtons)

        self.short_break_spin = QSpinBox()
        self.short_break_spin.setRange(1, 60)
        self.short_break_spin.setValue(short_break_minutes)
        self.short_break_spin.setButtonSymbols(QSpinBox.NoButtons)

        self.long_break_spin = QSpinBox()
        self.long_break_spin.setRange(1, 120)
        self.long_break_spin.setValue(long_break_minutes)
        self.long_break_spin.setButtonSymbols(QSpinBox.NoButtons)

        self.cycle_spin = QSpinBox()
        self.cycle_spin.setRange(1, 12)
        self.cycle_spin.setValue(cycle_length)
        self.cycle_spin.setButtonSymbols(QSpinBox.NoButtons)

        # Sound notification settings
        self.sound_combo = QComboBox()
        self.sound_combo.setView(QListView())
        self.sound_combo.addItems(["System Beep", "Custom Sound", "No Sound"])
        if notification_sound == "system":
            self.sound_combo.setCurrentIndex(0)
        elif notification_sound == "custom":
            self.sound_combo.setCurrentIndex(1)
        else:
            self.sound_combo.setCurrentIndex(2)
        self._apply_sound_combo_style()
            
        self.sound_file_button = QPushButton("Browse...")
        self.sound_file_button.clicked.connect(self._browse_sound_file)
        self.custom_sound_file = custom_sound_file
        
        # Update button text if file is already selected
        if self.custom_sound_file:
            import os
            filename = os.path.basename(self.custom_sound_file)
            self.sound_file_button.setText(f"Selected: {filename}")
        
        # Skip behavior setting
        self.skip_checkbox = QCheckBox("Skip increments cycle count")
        self.skip_checkbox.setChecked(skip_increments_cycle)
        self.skip_checkbox.setToolTip("When checked, skipping a focus session will still count toward cycle progress")

        self.theme_combo = QComboBox()
        self.theme_combo.setView(QListView())
        self.theme_combo.addItems(["OSRS Mode", "Normal Mode"])
        self.theme_combo.setCurrentIndex(0 if current_theme == "runescape" else 1)

        self.min_log_spin = QSpinBox()
        self.min_log_spin.setRange(0, 3600)
        self.min_log_spin.setValue(max(0, int(minimum_log_seconds)))
        self.min_log_spin.setButtonSymbols(QSpinBox.NoButtons)
        self.min_log_spin.setToolTip("Minimum active focus seconds before a segment is added to history. Set 0 to log all segments.")

        form_layout.addRow("Focus:", self.focus_spin)
        form_layout.addRow("Short Break:", self.short_break_spin)
        form_layout.addRow("Long Break:", self.long_break_spin)
        form_layout.addRow("Cycles:", self.cycle_spin)
        form_layout.addRow("Color Mode:", self.theme_combo)
        form_layout.addRow("Min Log Seconds:", self.min_log_spin)
        form_layout.addRow("Notification Sound:", self.sound_combo)
        form_layout.addRow("Custom Sound File:", self.sound_file_button)
        form_layout.addRow("", self.skip_checkbox)

        layout.addLayout(form_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _apply_sound_combo_style(self):
        """Ensure the sound dropdown and popup match the selected app theme."""
        theme = getattr(self.parent(), "_theme", "runescape")
        if theme == "runescape":
            combo_style = """
            QComboBox {
                background-color: #1a1a1a;
                color: #d8ccb2;
                border: 1px solid #3a3125;
                border-radius: 4px;
                padding: 4px 8px;
                min-height: 20px;
            }
            QComboBox:hover {
                border-color: #694d23;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid #3a3125;
                background-color: #2b251b;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0px;
                height: 0px;
            }
            QComboBox QAbstractItemView {
                background-color: #161616;
                color: #d8ccb2;
                border: 1px solid #3a3125;
                selection-background-color: #2b2218;
                selection-color: #e6a519;
            }
            """
        else:
            combo_style = """
            QComboBox {
                background-color: #1e1e1e;
                color: #f0f0f0;
                border: 1px solid #333333;
                border-radius: 4px;
                padding: 4px 8px;
                min-height: 20px;
            }
            QComboBox:hover {
                border-color: #555555;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid #333333;
                background-color: #2d2d2d;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0px;
                height: 0px;
            }
            QComboBox QAbstractItemView {
                background-color: #1e1e1e;
                color: #f0f0f0;
                border: 1px solid #333333;
                selection-background-color: #3a3a3a;
                selection-color: #ffffff;
            }
            """
        self.sound_combo.setStyleSheet(combo_style)
        
    def _browse_sound_file(self):
        """Opens a file dialog to select a custom sound file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Sound File", "", 
            "Sound Files (*.wav *.mp3 *.ogg *.m4a);;All Files (*)"
        )
        if file_path:
            self.custom_sound_file = file_path
            import os
            filename = os.path.basename(file_path)
            self.sound_file_button.setText(f"Selected: {filename}")

    def get_values(self):
        """Returns the selected durations, cycle length, and settings."""
        # Convert sound combo selection to setting string
        sound_options = ["system", "custom", "none"]
        sound_setting = sound_options[self.sound_combo.currentIndex()]
        theme_setting = "runescape" if self.theme_combo.currentIndex() == 0 else "dark"
        
        return (
            self.focus_spin.value(),
            self.short_break_spin.value(),
            self.long_break_spin.value(),
            self.cycle_spin.value(),
            sound_setting,
            self.custom_sound_file,
            self.skip_checkbox.isChecked(),
            self.min_log_spin.value(),
            theme_setting,
        )


def main():
    app = QApplication(sys.argv)
    icon_path = _resource_path(os.path.join("assets", "xpwaste.ico"))
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    window = XPWasteWindow()
    window.resize(480, 600)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

