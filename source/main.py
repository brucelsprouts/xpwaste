import sys
import json
import os
from datetime import datetime

from PyQt5.QtCore import Qt, QUrl, QTimer
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen, QIcon, QFont, QLinearGradient
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
    QMenu,
    QProgressBar,
    QSizePolicy,
    QGraphicsDropShadowEffect,
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


# ---------------------------------------------------------------------------
# Custom circular progress widget for the timer
# ---------------------------------------------------------------------------
class CircularProgress(QWidget):
    """A circular arc that shows timer progress."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 1.0  # 0.0 to 1.0
        self._arc_color = QColor("#e6a519")
        self._track_color = QColor(255, 255, 255, 20)
        self._arc_width = 6
        self.setMinimumSize(200, 200)
        self.setMaximumSize(200, 200)

    def set_progress(self, value):
        self._progress = max(0.0, min(1.0, value))
        self.update()

    def set_arc_color(self, color):
        self._arc_color = QColor(color)
        self.update()

    def set_track_color(self, color):
        self._track_color = QColor(color)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        size = min(self.width(), self.height())
        margin = self._arc_width + 2
        rect = self.rect().adjusted(margin, margin, -margin, -margin)

        # Track (background circle)
        pen = QPen(self._track_color, self._arc_width)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawEllipse(rect)

        # Progress arc
        if self._progress > 0.001:
            pen = QPen(self._arc_color, self._arc_width)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            start_angle = 90 * 16  # 12 o'clock position
            span_angle = int(-self._progress * 360 * 16)
            painter.drawArc(rect, start_angle, span_angle)

        painter.end()


# ---------------------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------------------
class XPWasteWindow(QMainWindow):
    """
    Main application window that connects the XPWaste logic to the UI.
    Handles start/pause/reset controls, history display, total study time,
    simple notifications, and optional duration customization.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("XPWaste")

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

        # Live "today" refresh timer — updates the today card every 30s
        self._today_refresh_timer = QTimer(self)
        self._today_refresh_timer.setInterval(30000)
        self._today_refresh_timer.timeout.connect(self._update_today_card)

        # Build UI and connect logic
        self._build_ui()
        self._connect_signals()
        self._load_existing_history()
        self._update_total_time_label()
        self._update_today_card()
        self._today_refresh_timer.start()

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
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 8, 16, 16)
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Menu bar / settings
        menu_bar = self.menuBar()
        settings_menu = menu_bar.addMenu("&Settings")
        durations_action = settings_menu.addAction("Timer Durations...")
        durations_action.triggered.connect(self._open_duration_settings)
        settings_menu.addSeparator()
        about_action = settings_menu.addAction("About XPWaste...")
        about_action.triggered.connect(self._show_about_dialog)

        # Title
        title_label = QLabel("XPWaste")
        title_label.setObjectName("TitleLabel")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # ── Session type tab buttons ──
        session_tab_layout = QHBoxLayout()
        session_tab_layout.setSpacing(0)
        self.focus_session_button = QPushButton("Focus")
        self.focus_session_button.setObjectName("SessionTab")
        self.focus_session_button.setProperty("active", True)
        self.short_break_button = QPushButton("Short Break")
        self.short_break_button.setObjectName("SessionTab")
        self.long_break_button = QPushButton("Long Break")
        self.long_break_button.setObjectName("SessionTab")
        session_tab_layout.addWidget(self.focus_session_button)
        session_tab_layout.addWidget(self.short_break_button)
        session_tab_layout.addWidget(self.long_break_button)
        main_layout.addLayout(session_tab_layout)

        # ── Session / timer card ──
        self.session_box = QFrame()
        self.session_box.setObjectName("SessionBox")
        session_box_layout = QVBoxLayout()
        session_box_layout.setSpacing(2)
        session_box_layout.setContentsMargins(16, 16, 16, 16)
        self.session_box.setLayout(session_box_layout)

        # Session type label
        self.session_label = QLabel(f"{self.timer.current_session_type}")
        self.session_label.setObjectName("SessionLabel")
        self.session_label.setAlignment(Qt.AlignCenter)
        session_box_layout.addWidget(self.session_label)

        # Circular progress + time display (stacked)
        timer_container = QWidget()
        timer_container.setObjectName("TimerContainer")
        timer_container_layout = QVBoxLayout()
        timer_container_layout.setContentsMargins(0, 0, 0, 0)
        timer_container_layout.setAlignment(Qt.AlignCenter)
        timer_container.setLayout(timer_container_layout)

        # Circular progress ring with time label overlaid
        self.circular_progress = CircularProgress()
        self.circular_progress.setFixedSize(180, 180)

        # Time label overlaid on the circle
        self.time_label = QLabel(self._format_time(self.timer.time_remaining))
        self.time_label.setObjectName("TimeLabel")
        self.time_label.setAlignment(Qt.AlignCenter)

        # Use a stacked layout approach via absolute positioning
        ring_wrapper = QWidget()
        ring_wrapper.setObjectName("RingWrapper")
        ring_wrapper.setFixedSize(180, 180)
        self.circular_progress.setParent(ring_wrapper)
        self.circular_progress.move(0, 0)
        self.time_label.setParent(ring_wrapper)
        self.time_label.setFixedSize(180, 180)
        self.time_label.move(0, 0)

        timer_container_layout.addWidget(ring_wrapper, alignment=Qt.AlignCenter)
        session_box_layout.addWidget(timer_container, alignment=Qt.AlignCenter)

        # Cycle info label with inline controls
        cycle_layout = QHBoxLayout()
        cycle_layout.setAlignment(Qt.AlignCenter)
        self.cycle_minus_button = QPushButton("-")
        self.cycle_minus_button.setObjectName("CycleButton")
        self.cycle_minus_button.setFixedSize(24, 24)
        self.cycle_label = QLabel("")
        self.cycle_label.setObjectName("CycleLabel")
        self.cycle_label.setAlignment(Qt.AlignCenter)
        self.cycle_plus_button = QPushButton("+")
        self.cycle_plus_button.setObjectName("CycleButton")
        self.cycle_plus_button.setFixedSize(24, 24)
        cycle_layout.addWidget(self.cycle_minus_button)
        cycle_layout.addWidget(self.cycle_label)
        cycle_layout.addWidget(self.cycle_plus_button)
        session_box_layout.addLayout(cycle_layout)

        main_layout.addWidget(self.session_box)

        # ── Control buttons ──
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(8)
        self.start_pause_button = QPushButton("Start")
        self.start_pause_button.setObjectName("PrimaryButton")
        self.skip_button = QPushButton("Skip")
        self.skip_button.setObjectName("SecondaryButton")
        self.reset_button = QPushButton("Reset")
        self.reset_button.setObjectName("SecondaryButton")
        controls_layout.addWidget(self.start_pause_button)
        controls_layout.addWidget(self.skip_button)
        controls_layout.addWidget(self.reset_button)
        main_layout.addLayout(controls_layout)

        # ── Today's Progress card ──
        self.today_card = QFrame()
        self.today_card.setObjectName("TodayCard")
        today_layout = QVBoxLayout()
        today_layout.setSpacing(8)
        today_layout.setContentsMargins(14, 12, 14, 12)
        self.today_card.setLayout(today_layout)

        today_header = QLabel("Today's Progress")
        today_header.setObjectName("TodayHeader")
        today_layout.addWidget(today_header)

        # Stats row: time studied | sessions
        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)

        # Time studied today
        time_stat = QVBoxLayout()
        time_stat.setSpacing(2)
        self.today_time_value = QLabel("0m 0s")
        self.today_time_value.setObjectName("TodayStatValue")
        time_stat_label = QLabel("Time Studied")
        time_stat_label.setObjectName("TodayStatLabel")
        time_stat.addWidget(self.today_time_value)
        time_stat.addWidget(time_stat_label)
        stats_row.addLayout(time_stat)

        # Separator line
        sep = QFrame()
        sep.setObjectName("StatSeparator")
        sep.setFrameShape(QFrame.VLine)
        sep.setFixedWidth(1)
        stats_row.addWidget(sep)

        # Sessions count today
        session_stat = QVBoxLayout()
        session_stat.setSpacing(2)
        self.today_sessions_value = QLabel("0")
        self.today_sessions_value.setObjectName("TodayStatValue")
        session_stat_label = QLabel("Sessions")
        session_stat_label.setObjectName("TodayStatLabel")
        session_stat.addWidget(self.today_sessions_value)
        session_stat.addWidget(session_stat_label)
        stats_row.addLayout(session_stat)

        # Separator
        sep2 = QFrame()
        sep2.setObjectName("StatSeparator")
        sep2.setFrameShape(QFrame.VLine)
        sep2.setFixedWidth(1)
        stats_row.addWidget(sep2)

        # Total all-time
        total_stat = QVBoxLayout()
        total_stat.setSpacing(2)
        self.today_total_value = QLabel("0m 0s")
        self.today_total_value.setObjectName("TodayStatValue")
        total_stat_label = QLabel("All Time")
        total_stat_label.setObjectName("TodayStatLabel")
        total_stat.addWidget(self.today_total_value)
        total_stat.addWidget(total_stat_label)
        stats_row.addLayout(total_stat)

        today_layout.addLayout(stats_row)

        # Daily progress bar (visual only — shows fraction of 2h goal)
        self.daily_progress = QProgressBar()
        self.daily_progress.setObjectName("DailyProgress")
        self.daily_progress.setRange(0, 100)
        self.daily_progress.setValue(0)
        self.daily_progress.setTextVisible(False)
        self.daily_progress.setFixedHeight(6)
        today_layout.addWidget(self.daily_progress)

        main_layout.addWidget(self.today_card)

        # ── History section ──
        history_group = QGroupBox("History")
        history_group.setObjectName("HistoryGroup")
        history_layout = QVBoxLayout()
        history_layout.setSpacing(4)
        history_group.setLayout(history_layout)

        self.overall_time_label = QLabel("")
        self.overall_time_label.setObjectName("HistoryOverallLabel")
        self.overall_time_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        history_layout.addWidget(self.overall_time_label)

        self.history_list = QListWidget()
        self.history_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.history_list.customContextMenuRequested.connect(self._show_history_context_menu)
        history_layout.addWidget(self.history_list)

        main_layout.addWidget(history_group)

        # Apply theme styling
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

    # ------------------------------------------------------------------ #
    # Theming
    # ------------------------------------------------------------------ #
    def _apply_theme(self):
        """Applies the current theme (runescape or normal) to the whole window."""
        if self._theme == "runescape":
            style = self._osrs_stylesheet()
        else:
            style = self._dark_stylesheet()

        self.setStyleSheet(style)
        # Set initial session background state
        self._update_session_background(self.timer.current_session_type)
        self._update_session_tab_highlight()
        self._update_circular_progress_colors()

    def _osrs_stylesheet(self):
        return """
        /* ── Base ── */
        QWidget {
            color: #d8ccb2;
            font-family: "Segoe UI", sans-serif;
            background-color: #0e0e0e;
        }
        QDialog { background-color: #0e0e0e; }

        /* ── Menu ── */
        QMenuBar {
            background-color: #0e0e0e;
            color: #bfa67a;
            border: none;
            font-size: 12px;
        }
        QMenuBar::item:selected { background-color: #1a1714; }
        QMenu {
            background-color: #141210;
            color: #d8ccb2;
            border: 1px solid #2e2618;
        }
        QMenu::item:selected {
            background-color: #2b2218;
            color: #ffcf3f;
        }

        /* ── Title ── */
        #TitleLabel {
            font-size: 26px;
            font-weight: 700;
            letter-spacing: 2px;
            color: #e6a519;
            margin: 6px 0 2px 0;
            background: transparent;
        }

        /* ── Session tab buttons ── */
        #SessionTab {
            background-color: #1a1714;
            color: #8c7d65;
            border: 1px solid #2e2618;
            padding: 7px 0;
            font-size: 13px;
            font-weight: 600;
        }
        #SessionTab:hover {
            background-color: #211d16;
            color: #bfa67a;
        }
        #SessionTab[active="true"] {
            background-color: #2b2218;
            color: #e6a519;
            border-bottom: 2px solid #e6a519;
        }

        /* ── Session box (timer card) ── */
        #SessionBox {
            border-radius: 10px;
            padding: 8px;
            border: 1px solid #2e2618;
        }
        #SessionBox[sessionType="focus"] {
            background-color: #161310;
            border-color: #4a3820;
        }
        #SessionBox[sessionType="short_break"] {
            background-color: #121a16;
            border-color: #2a4d36;
        }
        #SessionBox[sessionType="long_break"] {
            background-color: #121620;
            border-color: #2a3d5a;
        }

        /* ── Timer labels ── */
        #SessionLabel {
            font-size: 15px;
            font-weight: 600;
            margin: 4px 0;
            color: #bfa67a;
            background: transparent;
        }
        #TimeLabel {
            font-size: 42px;
            font-weight: 700;
            color: #ffcf3f;
            background: transparent;
        }
        #RingWrapper, #TimerContainer { background: transparent; }
        #CycleLabel {
            font-size: 12px;
            margin: 2px 0;
            color: #8c7d65;
            background: transparent;
        }

        /* ── Cycle +/- buttons ── */
        #CycleButton {
            border: 1px solid #2e2618;
            border-radius: 12px;
            background-color: #1a1714;
            color: #8c7d65;
            font-size: 14px;
            font-weight: 700;
            padding: 0;
        }
        #CycleButton:hover { background-color: #2b2218; color: #e6a519; }

        /* ── Control buttons ── */
        #PrimaryButton {
            background-color: #3d2e0f;
            color: #ffcf3f;
            border: 1px solid #5c4316;
            border-radius: 6px;
            padding: 8px 18px;
            font-size: 14px;
            font-weight: 700;
        }
        #PrimaryButton:hover { background-color: #4d3a14; border-color: #7a5a1e; }
        #PrimaryButton:pressed { background-color: #2e2208; }

        #SecondaryButton {
            background-color: #1a1714;
            color: #bfa67a;
            border: 1px solid #2e2618;
            border-radius: 6px;
            padding: 8px 18px;
            font-size: 14px;
            font-weight: 600;
        }
        #SecondaryButton:hover { background-color: #211d16; border-color: #4a3820; }
        #SecondaryButton:pressed { background-color: #0e0c0a; }

        /* ── Today's Progress card ── */
        #TodayCard {
            background-color: #141210;
            border: 1px solid #2e2618;
            border-radius: 8px;
        }
        #TodayHeader {
            font-size: 13px;
            font-weight: 700;
            color: #bfa67a;
            background: transparent;
            margin-bottom: 2px;
        }
        #TodayStatValue {
            font-size: 20px;
            font-weight: 700;
            color: #e6a519;
            background: transparent;
        }
        #TodayStatLabel {
            font-size: 11px;
            color: #6d6050;
            background: transparent;
        }
        #StatSeparator {
            background-color: #2e2618;
            max-height: 32px;
        }

        /* ── Daily progress bar ── */
        #DailyProgress {
            background-color: #1a1714;
            border: none;
            border-radius: 3px;
        }
        #DailyProgress::chunk {
            background-color: #b8860b;
            border-radius: 3px;
        }

        /* ── History ── */
        #HistoryGroup {
            border: 1px solid #2e2618;
            border-radius: 6px;
            margin-top: 8px;
            color: #bfa67a;
            font-weight: 600;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 4px;
        }
        #HistoryOverallLabel {
            font-size: 12px;
            margin: 2px 2px 4px 2px;
            color: #6d6050;
        }
        QListWidget {
            background-color: #111111;
            border: 1px solid #2e2618;
            border-radius: 4px;
            color: #c0b090;
            outline: 0;
            font-size: 12px;
        }
        QListWidget::item {
            padding: 4px 6px;
            border-bottom: 1px solid #1a1714;
        }
        QListWidget::item:selected {
            background-color: #2b2218;
            color: #e6a519;
        }
        QListWidget::item:focus { outline: none; }

        /* ── Spin boxes ── */
        QSpinBox {
            background-color: #141210;
            color: #d8ccb2;
            border: 1px solid #2e2618;
            border-radius: 4px;
            padding: 4px 8px;
            min-height: 20px;
        }
        QSpinBox::up-button, QSpinBox::down-button { width: 0px; border: none; }
        QSpinBox::up-arrow, QSpinBox::down-arrow { image: none; width: 0px; height: 0px; }

        /* ── Combo boxes ── */
        QComboBox {
            background-color: #141210;
            color: #d8ccb2;
            border: 1px solid #2e2618;
            border-radius: 4px;
            padding: 4px 8px;
            min-height: 20px;
        }
        QComboBox:hover { border-color: #4a3820; }
        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 20px;
            border-left: 1px solid #2e2618;
            background-color: #1a1714;
        }
        QComboBox::down-arrow { image: none; width: 0px; height: 0px; }
        QComboBox QAbstractItemView {
            background-color: #141210;
            color: #d8ccb2;
            border: 1px solid #2e2618;
            selection-background-color: #2b2218;
            selection-color: #e6a519;
        }

        /* ── Check boxes ── */
        QCheckBox { color: #d8ccb2; spacing: 8px; }
        QCheckBox::indicator {
            width: 14px; height: 14px;
            border: 1px solid #2e2618;
            border-radius: 3px;
            background-color: #141210;
        }
        QCheckBox::indicator:checked {
            background-color: #694d23;
            border-color: #8a6a3a;
        }
        QCheckBox::indicator:hover { border-color: #4a3820; }

        /* ── Scrollbars ── */
        QScrollBar:vertical {
            background-color: transparent; width: 7px; border: none; margin: 0;
        }
        QScrollBar::handle:vertical {
            background-color: #3a3020; border-radius: 3px; min-height: 20px;
        }
        QScrollBar::handle:vertical:hover { background-color: #4a3a24; }
        QScrollBar:horizontal {
            background-color: transparent; height: 7px; border: none; margin: 0;
        }
        QScrollBar::handle:horizontal {
            background-color: #3a3020; border-radius: 3px; min-width: 20px;
        }
        QScrollBar::handle:horizontal:hover { background-color: #4a3a24; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0px; height: 0px;
        }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
            background: transparent;
        }

        /* ── Dialog buttons ── */
        QPushButton {
            background-color: #1a1714;
            color: #bfa67a;
            border: 1px solid #2e2618;
            border-radius: 5px;
            padding: 6px 14px;
            font-size: 13px;
        }
        QPushButton:hover { background-color: #211d16; border-color: #4a3820; }
        QPushButton:pressed { background-color: #0e0c0a; color: #e6a519; }
        """

    def _dark_stylesheet(self):
        return """
        /* ── Base ── */
        QWidget {
            color: #e0e0e0;
            font-family: "Segoe UI", sans-serif;
            background-color: #0f0f0f;
        }
        QDialog { background-color: #0f0f0f; }

        /* ── Menu ── */
        QMenuBar {
            background-color: #0f0f0f;
            color: #a0a0a0;
            border: none;
            font-size: 12px;
        }
        QMenuBar::item:selected { background-color: #1a1a1a; }
        QMenu {
            background-color: #141414;
            color: #e0e0e0;
            border: 1px solid #2a2a2a;
        }
        QMenu::item:selected {
            background-color: #1e3a5f;
            color: #64b5f6;
        }

        /* ── Title ── */
        #TitleLabel {
            font-size: 26px;
            font-weight: 700;
            letter-spacing: 2px;
            color: #64b5f6;
            margin: 6px 0 2px 0;
            background: transparent;
        }

        /* ── Session tab buttons ── */
        #SessionTab {
            background-color: #161616;
            color: #707070;
            border: 1px solid #2a2a2a;
            padding: 7px 0;
            font-size: 13px;
            font-weight: 600;
        }
        #SessionTab:hover {
            background-color: #1e1e1e;
            color: #a0a0a0;
        }
        #SessionTab[active="true"] {
            background-color: #1a2a3a;
            color: #64b5f6;
            border-bottom: 2px solid #64b5f6;
        }

        /* ── Session box (timer card) ── */
        #SessionBox {
            border-radius: 10px;
            padding: 8px;
            border: 1px solid #2a2a2a;
        }
        #SessionBox[sessionType="focus"] {
            background-color: #141414;
            border-color: #2a2a2a;
        }
        #SessionBox[sessionType="short_break"] {
            background-color: #0f1a14;
            border-color: #1a3a28;
        }
        #SessionBox[sessionType="long_break"] {
            background-color: #0f1420;
            border-color: #1a2a4a;
        }

        /* ── Timer labels ── */
        #SessionLabel {
            font-size: 15px;
            font-weight: 600;
            margin: 4px 0;
            color: #909090;
            background: transparent;
        }
        #TimeLabel {
            font-size: 42px;
            font-weight: 700;
            color: #f0f0f0;
            background: transparent;
        }
        #RingWrapper, #TimerContainer { background: transparent; }
        #CycleLabel {
            font-size: 12px;
            margin: 2px 0;
            color: #606060;
            background: transparent;
        }

        /* ── Cycle +/- buttons ── */
        #CycleButton {
            border: 1px solid #2a2a2a;
            border-radius: 12px;
            background-color: #161616;
            color: #707070;
            font-size: 14px;
            font-weight: 700;
            padding: 0;
        }
        #CycleButton:hover { background-color: #1e1e1e; color: #64b5f6; }

        /* ── Control buttons ── */
        #PrimaryButton {
            background-color: #1a3050;
            color: #64b5f6;
            border: 1px solid #264a70;
            border-radius: 6px;
            padding: 8px 18px;
            font-size: 14px;
            font-weight: 700;
        }
        #PrimaryButton:hover { background-color: #1e3a5f; border-color: #3a6090; }
        #PrimaryButton:pressed { background-color: #0f1e30; }

        #SecondaryButton {
            background-color: #161616;
            color: #a0a0a0;
            border: 1px solid #2a2a2a;
            border-radius: 6px;
            padding: 8px 18px;
            font-size: 14px;
            font-weight: 600;
        }
        #SecondaryButton:hover { background-color: #1e1e1e; border-color: #3a3a3a; }
        #SecondaryButton:pressed { background-color: #0a0a0a; }

        /* ── Today's Progress card ── */
        #TodayCard {
            background-color: #141414;
            border: 1px solid #2a2a2a;
            border-radius: 8px;
        }
        #TodayHeader {
            font-size: 13px;
            font-weight: 700;
            color: #909090;
            background: transparent;
            margin-bottom: 2px;
        }
        #TodayStatValue {
            font-size: 20px;
            font-weight: 700;
            color: #64b5f6;
            background: transparent;
        }
        #TodayStatLabel {
            font-size: 11px;
            color: #505050;
            background: transparent;
        }
        #StatSeparator {
            background-color: #2a2a2a;
            max-height: 32px;
        }

        /* ── Daily progress bar ── */
        #DailyProgress {
            background-color: #1a1a1a;
            border: none;
            border-radius: 3px;
        }
        #DailyProgress::chunk {
            background-color: #2979ff;
            border-radius: 3px;
        }

        /* ── History ── */
        #HistoryGroup {
            border: 1px solid #2a2a2a;
            border-radius: 6px;
            margin-top: 8px;
            color: #909090;
            font-weight: 600;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 4px;
        }
        #HistoryOverallLabel {
            font-size: 12px;
            margin: 2px 2px 4px 2px;
            color: #505050;
        }
        QListWidget {
            background-color: #111111;
            border: 1px solid #2a2a2a;
            border-radius: 4px;
            color: #b0b0b0;
            outline: 0;
            font-size: 12px;
        }
        QListWidget::item {
            padding: 4px 6px;
            border-bottom: 1px solid #1a1a1a;
        }
        QListWidget::item:selected {
            background-color: #1a2a3a;
            color: #64b5f6;
        }
        QListWidget::item:focus { outline: none; }

        /* ── Spin boxes ── */
        QSpinBox {
            background-color: #141414;
            color: #e0e0e0;
            border: 1px solid #2a2a2a;
            border-radius: 4px;
            padding: 4px 8px;
            min-height: 20px;
        }
        QSpinBox::up-button, QSpinBox::down-button { width: 0px; border: none; }
        QSpinBox::up-arrow, QSpinBox::down-arrow { image: none; width: 0px; height: 0px; }

        /* ── Combo boxes ── */
        QComboBox {
            background-color: #141414;
            color: #e0e0e0;
            border: 1px solid #2a2a2a;
            border-radius: 4px;
            padding: 4px 8px;
            min-height: 20px;
        }
        QComboBox:hover { border-color: #3a3a3a; }
        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 20px;
            border-left: 1px solid #2a2a2a;
            background-color: #1a1a1a;
        }
        QComboBox::down-arrow { image: none; width: 0px; height: 0px; }
        QComboBox QAbstractItemView {
            background-color: #141414;
            color: #e0e0e0;
            border: 1px solid #2a2a2a;
            selection-background-color: #1a2a3a;
            selection-color: #64b5f6;
        }

        /* ── Check boxes ── */
        QCheckBox { color: #e0e0e0; spacing: 8px; }
        QCheckBox::indicator {
            width: 14px; height: 14px;
            border: 1px solid #2a2a2a;
            border-radius: 3px;
            background-color: #141414;
        }
        QCheckBox::indicator:checked {
            background-color: #2979ff;
            border-color: #448aff;
        }
        QCheckBox::indicator:hover { border-color: #3a3a3a; }

        /* ── Scrollbars ── */
        QScrollBar:vertical {
            background-color: transparent; width: 7px; border: none; margin: 0;
        }
        QScrollBar::handle:vertical {
            background-color: #2a2a2a; border-radius: 3px; min-height: 20px;
        }
        QScrollBar::handle:vertical:hover { background-color: #3a3a3a; }
        QScrollBar:horizontal {
            background-color: transparent; height: 7px; border: none; margin: 0;
        }
        QScrollBar::handle:horizontal {
            background-color: #2a2a2a; border-radius: 3px; min-width: 20px;
        }
        QScrollBar::handle:horizontal:hover { background-color: #3a3a3a; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0px; height: 0px;
        }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
            background: transparent;
        }

        /* ── Dialog buttons ── */
        QPushButton {
            background-color: #161616;
            color: #a0a0a0;
            border: 1px solid #2a2a2a;
            border-radius: 5px;
            padding: 6px 14px;
            font-size: 13px;
        }
        QPushButton:hover { background-color: #1e1e1e; border-color: #3a3a3a; }
        QPushButton:pressed { background-color: #0a0a0a; color: #64b5f6; }
        """

    def _update_session_tab_highlight(self):
        """Updates the active state on session tab buttons."""
        current = self.timer.current_session_type
        for btn, stype in [
            (self.focus_session_button, "Focus"),
            (self.short_break_button, "Short Break"),
            (self.long_break_button, "Long Break"),
        ]:
            btn.setProperty("active", current == stype)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _update_circular_progress_colors(self):
        """Sets the circular progress ring colors based on session type and theme."""
        session = self.timer.current_session_type
        if self._theme == "runescape":
            colors = {
                "Focus": ("#e6a519", "rgba(230, 165, 25, 25)"),
                "Short Break": ("#4a9d6a", "rgba(74, 157, 106, 25)"),
                "Long Break": ("#4a7db8", "rgba(74, 125, 184, 25)"),
            }
        else:
            colors = {
                "Focus": ("#64b5f6", "rgba(100, 181, 246, 20)"),
                "Short Break": ("#66bb6a", "rgba(102, 187, 106, 20)"),
                "Long Break": ("#7e57c2", "rgba(126, 87, 194, 20)"),
            }
        arc, track = colors.get(session, colors["Focus"])
        self.circular_progress.set_arc_color(arc)
        self.circular_progress.set_track_color(track)

    def _set_theme(self, theme: str):
        """Updates the current theme and reapplies styles without touching timer state."""
        if theme not in ("runescape", "dark"):
            return
        self._theme = theme
        self._apply_theme()
        self._refresh_history_list()
        self._update_today_card()
        # Resync display widgets — theme change must never affect timer state
        self._update_circular_progress_value()
        self._update_start_pause_button()
        self.time_label.setText(self._format_time(self.timer.time_remaining))

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
        """Shows information about XPWaste prevention and efficient training."""
        about_text = """
    <h2>About XPWaste</h2>

    <p>XPWaste is a focused session timer for RuneScape players, built around a Pomodoro-style loop.
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
<li>Today's Progress card with daily stats and progress bar</li>
<li>Right-click history entries to remove them</li>
<li>Manual focus/break switching and cycle progress controls</li>
</ul>

<p><em>Tip: By default, skipping a focus session does not advance the cycle.
You can enable skip-to-increment behavior in Timer Settings. Active study time
counts only while the timer is running, so paused time is not included. Use
minimum history log seconds to avoid tiny history entries. Use right-click on
history rows to remove specific entries.</em></p>
        """

        msg = QMessageBox(self)
        msg.setWindowTitle("About XPWaste")
        msg.setTextFormat(Qt.RichText)
        msg.setText(about_text)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    # ------------------------------------------------------------------ #
    # Today's Progress
    # ------------------------------------------------------------------ #
    def _update_today_card(self):
        """Refreshes the Today's Progress card with current data."""
        today_seconds = self.history_manager.get_total_study_seconds_today()
        today_sessions = self.history_manager.get_focus_session_count_today()
        overall_seconds = self.history_manager.get_total_study_seconds_overall()

        self.today_time_value.setText(self._format_duration(today_seconds))
        self.today_sessions_value.setText(str(today_sessions))
        self.today_total_value.setText(self._format_duration(overall_seconds))

        # Progress bar: fraction of a 2-hour daily goal (7200s)
        daily_goal = 7200
        pct = min(100, int((today_seconds / daily_goal) * 100)) if daily_goal > 0 else 0
        self.daily_progress.setValue(pct)

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
        self._update_circular_progress_value()

    def _handle_skip(self):
        if self._skip_increments_cycle and self.timer.current_session_type == "Focus":
            # Skip but still increment cycle count
            self.timer.skip_current_session_with_increment()
        else:
            # Skip without incrementing cycle (default behavior)
            self.timer.skip_current_session()
        self._update_cycle_label()
        self._update_start_pause_button()
        self._update_today_card()

    def _handle_force_session(self, session_type: str):
        """Manually switches to a specific session type."""
        self.timer.force_session_type(session_type)
        self._update_cycle_label()
        self._update_start_pause_button()
        self._update_session_tab_highlight()
        self._update_circular_progress_colors()
        self._update_circular_progress_value()

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
            durations_changed = (
                focus != self.timer.FOCUS_TIME or
                short_break != self.timer.SHORT_BREAK_TIME or
                long_break != self.timer.LONG_BREAK_TIME
            )
            self.timer.set_durations(focus, short_break, long_break, reset_current=durations_changed)
            self.timer.set_cycle_length(cycle_length)
            self.timer.set_minimum_log_seconds(min_log_seconds)
            self._notification_sound = sound_setting
            self._custom_sound_file = sound_file
            self._skip_increments_cycle = skip_behavior
            self._minimum_log_seconds = min_log_seconds
            self._set_theme(selected_theme)
            self._save_settings()  # Save settings to file
            self._update_cycle_label()
            # Always resync display after any settings change
            self._update_start_pause_button()
            self._update_circular_progress_value()

    # ------------------------------------------------------------------ #
    # Timer signal handlers
    # ------------------------------------------------------------------ #
    def _on_countdown_updated(self, remaining_seconds):
        self.time_label.setText(self._format_time(remaining_seconds))
        self._update_circular_progress_value()

    def _on_session_changed(self, session_type):
        # Play notification sound
        self._play_notification_sound()

        # Pause timer so user must manually start next session
        self.timer.pause()

        self.session_label.setText(f"{session_type}")
        self._update_session_background(session_type)
        self._update_session_tab_highlight()
        self._update_circular_progress_colors()
        self._update_cycle_label()
        self._last_session_type = session_type
        self._update_start_pause_button()
        self._update_today_card()

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
        self._update_today_card()

    # ------------------------------------------------------------------ #
    # History helpers
    # ------------------------------------------------------------------ #
    def _add_history_item_to_list(self, session):
        """Adds a single session entry to the history list widget at the top."""
        text = self._format_history_item_text(session)
        item = QListWidgetItem(text)
        self.history_list.insertItem(0, item)  # Insert at top instead of bottom

    def _refresh_history_list(self):
        """Reloads history list text."""
        self.history_list.clear()
        for session in self.history_manager.get_history():
            self._add_history_item_to_list(session)

    def _show_history_context_menu(self, pos):
        """Shows right-click actions for a history row."""
        item = self.history_list.itemAt(pos)
        if item is None:
            return

        menu = QMenu(self)
        remove_action = menu.addAction("Remove Entry")
        selected_action = menu.exec_(self.history_list.mapToGlobal(pos))
        if selected_action == remove_action:
            row = self.history_list.row(item)
            self._remove_history_entry_by_row(row)

    def _remove_history_entry_by_row(self, row):
        """Removes a history item using UI row index (newest first display)."""
        history = self.history_manager.get_history()
        if row < 0 or row >= len(history):
            return

        history_index = len(history) - 1 - row
        if self.history_manager.remove_session_at(history_index):
            self._refresh_history_list()
            self._update_total_time_label()
            self._update_today_card()

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
        overall_seconds = self.history_manager.get_total_study_seconds_overall()
        self.overall_time_label.setText(f"Total: {self._format_duration(overall_seconds)}")
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
    # Circular progress
    # ------------------------------------------------------------------ #
    def _update_circular_progress_value(self):
        """Updates the circular progress ring based on remaining time."""
        session = self.timer.current_session_type
        if session == "Focus":
            total = self.timer.FOCUS_TIME * 60
        elif session == "Short Break":
            total = self.timer.SHORT_BREAK_TIME * 60
        else:
            total = self.timer.LONG_BREAK_TIME * 60

        remaining = self.timer.time_remaining
        progress = remaining / total if total > 0 else 1.0
        self.circular_progress.set_progress(progress)

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
    """Dialog window for adjusting XPWaste durations and cycle length."""

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
    window.resize(420, 720)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
