import sys
import json
import os
from datetime import datetime

from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen
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
)

from pomodoro_timer import XPWasteTimer
from session_history import SessionHistoryManager


class XPWasteWindow(QMainWindow):
    """
    Main application window that connects the XP Waste timer logic to the UI.
    Handles start/pause/reset controls, history display, total study time,
    simple notifications, and optional duration customization.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("XP Waste Timer")

        # Core logic objects
        self.timer = XPWasteTimer(self)
        self.history_manager = SessionHistoryManager()
        self._last_session_type = self.timer.current_session_type
        self._theme = "runescape"  # Default to RuneScape theme
        
        # Settings file path
        self._settings_file = os.path.join("data", "settings.json")
        
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
        
        try:
            if os.path.exists(self._settings_file):
                with open(self._settings_file, 'r') as f:
                    settings = json.load(f)
                    self._notification_sound = settings.get("notification_sound", "system")
                    self._custom_sound_file = settings.get("custom_sound_file", None)
                    self._skip_increments_cycle = settings.get("skip_increments_cycle", False)
                    
                    # Load timer settings
                    if "focus_time" in settings:
                        self.timer.FOCUS_TIME = settings["focus_time"]
                    if "short_break_time" in settings:
                        self.timer.SHORT_BREAK_TIME = settings["short_break_time"]
                    if "long_break_time" in settings:
                        self.timer.LONG_BREAK_TIME = settings["long_break_time"]
                    if "cycle_length" in settings:
                        self.timer.FOCUS_SESSIONS_BEFORE_LONG_BREAK = settings["cycle_length"]
        except Exception as e:
            print(f"Failed to load settings: {e}")
            
    def _save_settings(self):
        """Save settings to file."""
        try:
            os.makedirs("data", exist_ok=True)
            settings = {
                "notification_sound": self._notification_sound,
                "custom_sound_file": self._custom_sound_file,
                "skip_increments_cycle": self._skip_increments_cycle,
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
        about_action = settings_menu.addAction("About XP Waste Timer...")
        about_action.triggered.connect(self._show_about_dialog)
        self.theme_action = settings_menu.addAction("Switch to Light Mode")
        self.theme_action.triggered.connect(self._toggle_theme)

        # Title
        title_label = QLabel("XP Waste Timer")
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
        self.cycle_minus_button.setStyleSheet("QPushButton { border: none; background: transparent; font-weight: bold; font-size: 16px; padding: 0; }")
        self.cycle_label = QLabel("")
        self.cycle_label.setObjectName("CycleLabel")
        self.cycle_label.setAlignment(Qt.AlignCenter)
        self.cycle_plus_button = QPushButton("+")
        self.cycle_plus_button.setFlat(True)
        self.cycle_plus_button.setFixedSize(20, 20)
        self.cycle_plus_button.setStyleSheet("QPushButton { border: none; background: transparent; font-weight: bold; font-size: 16px; padding: 0; }")
        cycle_layout.addWidget(self.cycle_minus_button)
        cycle_layout.addWidget(self.cycle_label)
        cycle_layout.addWidget(self.cycle_plus_button)
        session_box_layout.addLayout(cycle_layout)

        main_layout.addWidget(self.session_box)

        # Control buttons
        controls_layout = QHBoxLayout()
        self.start_button = QPushButton("Start")
        self.pause_button = QPushButton("Pause")
        self.skip_button = QPushButton("Skip")
        self.reset_button = QPushButton("Reset")
        controls_layout.addWidget(self.start_button)
        controls_layout.addWidget(self.pause_button)
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
        self.start_button.clicked.connect(self._handle_start)
        self.pause_button.clicked.connect(self._handle_pause)
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

    def _load_existing_history(self):
        """Loads previously saved sessions into the history list."""
        for session in self.history_manager.get_history():
            self._add_history_item_to_list(session)

    def _apply_theme(self):
        """Applies the current theme (dark or light) to the whole window."""
        if self._theme == "dark":
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
                font-weight: bold;
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
                font-weight: bold;
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
        else:
            # Light theme
            style = """
            QWidget {
                color: #222222;
                font-family: Segoe UI, sans-serif;
                background-color: #f5f5f5;
            }
            QDialog {
                background-color: #ffffff;
            }
            QMenuBar {
                background-color: #f5f5f5;
                color: #222222;
                border: none;
            }
            QMenuBar::item:selected {
                background-color: #e0e0e0;
            }
            QMenu {
                background-color: #ffffff;
                color: #222222;
                border: 1px solid #cccccc;
            }
            QMenu::item:selected {
                background-color: #bbdefb;
            }
            #SessionBox {
                border-radius: 8px;
                padding: 8px;
            }
            #SessionBox[sessionType="focus"] {
                background-color: #e1f5fe;
                border: 1px solid #81d4fa;
            }
            #SessionBox[sessionType="short_break"] {
                background-color: #fff8e1;
                border: 1px solid #ffcc02;
            }
            #SessionBox[sessionType="long_break"] {
                background-color: #f1f8e9;
                border: 1px solid #81c784;
            }
            #TitleLabel {
                font-size: 24px;
                font-weight: bold;
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
                font-weight: bold;
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
                background-color: #ffffff;
                color: #222222;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 6px 14px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border-color: #aaaaaa;
            }
            QPushButton:pressed {
                background-color: #e8e8e8;
            }
            QGroupBox {
                border: 1px solid #cccccc;
                border-radius: 4px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            QListWidget {
                background-color: #ffffff;
                border: 1px solid #cccccc;
            }
            QSpinBox {
                background-color: #ffffff;
                color: #222222;
                border: 1px solid #bdbdbd;
                border-radius: 4px;
                padding: 4px 8px;
                min-height: 20px;
                selection-background-color: #ffffff;
                selection-color: #222222;
            }
            QSpinBox:focus {
                border-color: #1e88e5;
                selection-background-color: #ffffff;
                selection-color: #222222;
            }
            QSpinBox::up-button {
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 18px;
                border-left: 1px solid #bdbdbd;
                border-bottom: 1px solid #bdbdbd;
                border-top-right-radius: 4px;
                background-color: #f5f5f5;
            }
            QSpinBox::up-button:hover {
                background-color: #e8e8e8;
            }
            QSpinBox::up-button:pressed {
                background-color: #d0d0d0;
            }
            QSpinBox::down-button {
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 18px;
                border-left: 1px solid #bdbdbd;
                border-top: 1px solid #bdbdbd;
                border-bottom-right-radius: 4px;
                background-color: #f5f5f5;
            }
            QSpinBox::down-button:hover {
                background-color: #e8e8e8;
            }
            QSpinBox::down-button:pressed {
                background-color: #d0d0d0;
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
            QLabel {
                background-color: transparent;
                selection-background-color: transparent;
            }
            QFormLayout QLabel {
                background-color: transparent;
                selection-background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: transparent;
                width: 8px;
                border: none;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background-color: #c0c0c0;
                border-radius: 4px;
                min-height: 20px;
                margin: 0;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #a8a8a8;
            }
            QScrollBar::handle:vertical:pressed {
                background-color: #888888;
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
                background-color: #f0f0f0;
                height: 14px;
                border: 1px solid #d0d0d0;
                border-radius: 6px;
                margin: 0;
            }
            QScrollBar::handle:horizontal {
                background-color: #b8b8b8;
                border: 1px solid #9c9c9c;
                border-radius: 5px;
                min-width: 30px;
                margin: 1px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #a0a0a0;
                border-color: #808080;
            }
            QScrollBar::handle:horizontal:pressed {
                background-color: #888888;
            }
            QScrollBar::add-line:horizontal {
                border: 1px solid #d0d0d0;
                border-radius: 3px;
                background-color: #f8f8f8;
                width: 14px;
                subcontrol-position: right;
                subcontrol-origin: margin;
            }
            QScrollBar::add-line:horizontal:hover {
                background-color: #e8e8e8;
            }
            QScrollBar::sub-line:horizontal {
                border: 1px solid #d0d0d0;
                border-radius: 3px;
                background-color: #f8f8f8;
                width: 14px;
                subcontrol-position: left;
                subcontrol-origin: margin;
            }
            QScrollBar::sub-line:horizontal:hover {
                background-color: #e8e8e8;
            }
            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {
                background: none;
            }
            """

        self.setStyleSheet(style)
        # Set initial session background state
        self._update_session_background(self.timer.current_session_type)

    def _set_theme(self, theme: str):
        """Updates the current theme and reapplies styles."""
        if theme not in ("dark", "light"):
            return
        self._theme = theme
        self._apply_theme()

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

    def _toggle_theme(self):
        """Toggles between dark and light themes."""
        new_theme = "light" if self._theme == "dark" else "dark"
        self._set_theme(new_theme)
        # Update menu text
        if hasattr(self, "theme_action"):
            if self._theme == "dark":
                self.theme_action.setText("Switch to Light Mode")
            else:
                self.theme_action.setText("Switch to Dark Mode")

    def _show_about_dialog(self):
        """Shows information about the Pomodoro Technique and this timer."""
        about_text = """
<h2>About Pomodoro Timer</h2>

<h3>What is the Pomodoro Technique?</h3>
<p>The Pomodoro Technique is a time management method developed by Francesco Cirillo. 
It uses a timer to break down work into intervals, traditionally 25 minutes in length, 
separated by short breaks.</p>

<h3>How It Works:</h3>
<ol>
<li><strong>Focus Session (25 min):</strong> Work on a single task with full concentration</li>
<li><strong>Short Break (5 min):</strong> Take a brief break to rest and recharge</li>
<li><strong>Repeat:</strong> After 4 focus sessions, take a longer break (15 min)</li>
</ol>

<h3>This Timer Features:</h3>
<ul>
<li><strong>Automatic Cycles:</strong> Timer automatically switches between focus and break sessions</li>
<li><strong>Session Tracking:</strong> Completed focus sessions are saved to history</li>
<li><strong>Manual Controls:</strong> Skip sessions or manually switch session types</li>
<li><strong>Cycle Management:</strong> Use +/- buttons to adjust current cycle progress</li>
<li><strong>Customizable:</strong> Adjust session durations and cycle length in Settings</li>
<li><strong>Visual Feedback:</strong> Different colors for each session type</li>
</ul>

<p><em>Tip: Skipping a session won't count toward your cycle progress, 
only naturally completed focus sessions advance the cycle.</em></p>
        """
        
        msg = QMessageBox(self)
        msg.setWindowTitle("About XP Waste Timer")
        msg.setTextFormat(Qt.RichText)
        msg.setText(about_text)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    # ------------------------------------------------------------------ #
    # Button handlers
    # ------------------------------------------------------------------ #
    def _handle_start(self):
        self.timer.start()

    def _handle_pause(self):
        self.timer.pause()

    def _handle_reset(self):
        self.timer.reset()

    def _handle_skip(self):
        if self._skip_increments_cycle and self.timer.current_session_type == "Focus":
            # Skip but still increment cycle count
            self.timer.skip_current_session_with_increment()
        else:
            # Skip without incrementing cycle (default behavior)
            self.timer.skip_current_session()
        self._update_cycle_label()

    def _handle_force_session(self, session_type: str):
        """Manually switches to a specific session type."""
        self.timer.force_session_type(session_type)
        self._update_cycle_label()

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
            parent=self,
        )
        if dialog.exec_() == QDialog.Accepted:
            focus, short_break, long_break, cycle_length, sound_setting, sound_file, skip_behavior = dialog.get_values()
            self.timer.set_durations(focus, short_break, long_break, reset_current=True)
            self.timer.set_cycle_length(cycle_length)
            self._notification_sound = sound_setting
            self._custom_sound_file = sound_file
            self._skip_increments_cycle = skip_behavior
            self._save_settings()  # Save settings to file
            self._update_cycle_label()
            QMessageBox.information(self, "Settings Updated", "Timer settings have been updated.")

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
        duration_minutes = max(1, int(duration_seconds // 60))

        session_data = {
            "date": date_str,
            "start_time": start_str,
            "end_time": end_str,
            "duration": duration_minutes,
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
        date = session.get("date", "")
        start_time = session.get("start_time", "")
        end_time = session.get("end_time", "")
        duration = session.get("duration", 0)
        text = f"{date}  {start_time} - {end_time}  ({duration} min)"
        item = QListWidgetItem(text)
        self.history_list.insertItem(0, item)  # Insert at top instead of bottom

    def _update_total_time_label(self):
        total_minutes = self.history_manager.get_total_study_time_today()
        self.total_time_label.setText(f"Today's Focus Time: {total_minutes} min")
        overall_minutes = sum(
            session.get("duration", 0) for session in self.history_manager.get_history()
        )
        self.overall_time_label.setText(f"Overall Focus Time: {overall_minutes} min")
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
                 notification_sound="system", custom_sound_file=None, skip_increments_cycle=False, parent=None):
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
        self.sound_combo.addItems(["System Beep", "Custom Sound", "No Sound"])
        if notification_sound == "system":
            self.sound_combo.setCurrentIndex(0)
        elif notification_sound == "custom":
            self.sound_combo.setCurrentIndex(1)
        else:
            self.sound_combo.setCurrentIndex(2)
            
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

        form_layout.addRow("Focus:", self.focus_spin)
        form_layout.addRow("Short Break:", self.short_break_spin)
        form_layout.addRow("Long Break:", self.long_break_spin)
        form_layout.addRow("Cycles:", self.cycle_spin)
        form_layout.addRow("Notification Sound:", self.sound_combo)
        form_layout.addRow("Custom Sound File:", self.sound_file_button)
        form_layout.addRow("", self.skip_checkbox)

        layout.addLayout(form_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
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
        
        return (
            self.focus_spin.value(),
            self.short_break_spin.value(),
            self.long_break_spin.value(),
            self.cycle_spin.value(),
            sound_setting,
            self.custom_sound_file,
            self.skip_checkbox.isChecked(),
        )


def main():
    app = QApplication(sys.argv)
    window = XPWasteWindow()
    window.resize(480, 600)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

