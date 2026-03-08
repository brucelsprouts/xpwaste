from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from datetime import datetime, timedelta

class XPWasteTimer(QObject):
    # Signals
    countdown_updated = pyqtSignal(int)
    session_changed = pyqtSignal(str)
    focus_session_completed = pyqtSignal(str, str, int) # start_time (ISO), end_time (ISO), duration (seconds)

    # Constants for session durations in minutes
    FOCUS_TIME = 25
    SHORT_BREAK_TIME = 5
    LONG_BREAK_TIME = 15

    # Number of focus sessions before a long break
    FOCUS_SESSIONS_BEFORE_LONG_BREAK = 4

    def __init__(self, parent=None):
        super().__init__(parent)

        # Initialize session state
        self._current_session_type = "Focus"
        self._time_remaining = self.FOCUS_TIME * 60  # Convert minutes to seconds
        self._focus_sessions_completed = 0

        # Timer setup
        self._timer = QTimer(self)
        self._timer.setInterval(1000)  # 1 second interval
        self._timer.timeout.connect(self._tick)

        # Timer control flags and start time
        self._is_running = False
        self._start_time = None # datetime object when current session started

    def start(self):
        """Starts or resumes the XP Waste session."""
        if not self._is_running:
            self._is_running = True
            self._timer.start() # Start the QTimer
            self._start_time = datetime.now() # Record start time of the current session
            print(f"Timer started. Current session: {self._current_session_type}, Time remaining: {self._time_remaining}s")

    def pause(self):
        """Pauses the XP Waste session."""
        if self._is_running:
            self._is_running = False
            self._timer.stop() # Stop the QTimer
            print(f"Timer paused. Time remaining: {self._time_remaining}s")

    def reset(self):
        """Resets the timer to the beginning of the current session type and resets focus session count."""
        self.pause()
        self._focus_sessions_completed = 0
        self._set_session_duration(self._current_session_type) # Reset time remaining for current session type
        self.countdown_updated.emit(self._time_remaining)
        print(f"Timer reset. Current session: {self._current_session_type}, Time remaining: {self._time_remaining}s")

    def _tick(self):
        """Decrements time remaining and handles session changes when time runs out."""
        if self._time_remaining > 0:
            self._time_remaining -= 1
            self.countdown_updated.emit(self._time_remaining)
        else:
            # Session completed naturally
            self._change_session(completed_naturally=True)

    def _change_session(self, completed_naturally: bool):
        """Determines the next session type based on XP Waste rules and updates the timer state."""
        end_time = datetime.now()

        if self._current_session_type == "Focus":
            # Record elapsed focus time when a focus session ends naturally or is skipped.
            # Minutes are rounded down later in the UI layer; skip events only count if
            # at least one full minute has elapsed.
            if self._start_time:
                duration = (end_time - self._start_time).total_seconds()
                if completed_naturally or duration >= 60:
                    self.focus_session_completed.emit(
                        self._start_time.isoformat(),
                        end_time.isoformat(),
                        int(duration)
                    )

            # Update focus session counter only on natural completion
            if completed_naturally:
                self._focus_sessions_completed += 1

            # Decide next session type based on completed focus sessions
            if self._focus_sessions_completed > 0 and \
               self._focus_sessions_completed % self.FOCUS_SESSIONS_BEFORE_LONG_BREAK == 0:
                self._current_session_type = "Long Break"
                self._focus_sessions_completed = 0  # Reset focus session count after a long break
            else:
                self._current_session_type = "Short Break"
        elif self._current_session_type in ("Short Break", "Long Break"):
            self._current_session_type = "Focus"

        self._set_session_duration(self._current_session_type)
        # Don't auto-start the timer - user will need to press start
        self._is_running = False
        self._timer.stop()
        self.session_changed.emit(self._current_session_type)
        self.countdown_updated.emit(self._time_remaining)
        self._start_time = None  # Will be set when user presses start
        print(f"Session changed to: {self._current_session_type}. Time remaining: {self._time_remaining}s. Press start to begin.")

    def _set_session_duration(self, session_type):
        """Sets _time_remaining based on the given session type."""
        if session_type == "Focus":
            self._time_remaining = self.FOCUS_TIME * 60
        elif session_type == "Short Break":
            self._time_remaining = self.SHORT_BREAK_TIME * 60
        elif session_type == "Long Break":
            self._time_remaining = self.LONG_BREAK_TIME * 60

    @property
    def current_session_type(self):
        """Returns the current session type (e.g., 'Focus', 'Short Break')."""
        return self._current_session_type

    @property
    def time_remaining(self):
        """Returns the time remaining in the current session in seconds."""
        return self._time_remaining

    @property
    def is_running(self):
        """Returns True if the timer is currently running, False otherwise."""
        return self._is_running

    @property
    def start_time(self):
        """Returns the datetime object when the current session started."""
        return self._start_time

    def set_durations(self, focus_minutes, short_break_minutes, long_break_minutes, reset_current=True):
        """
        Updates the focus and break durations (in minutes).

        Args:
            focus_minutes (int): Duration of a focus session in minutes.
            short_break_minutes (int): Duration of a short break in minutes.
            long_break_minutes (int): Duration of a long break in minutes.
            reset_current (bool): If True, resets the remaining time for the
                                  current session to match the new duration
                                  and emits an updated countdown signal.
        """
        # Ensure durations are at least 1 minute
        self.FOCUS_TIME = max(1, int(focus_minutes))
        self.SHORT_BREAK_TIME = max(1, int(short_break_minutes))
        self.LONG_BREAK_TIME = max(1, int(long_break_minutes))

        if reset_current:
            self._set_session_duration(self._current_session_type)
            self.countdown_updated.emit(self._time_remaining)

    def skip_current_session(self):
        """
        Immediately ends the current session and transitions to the next one,
        without counting it as a completed focus session.
        """
        # Skip transitions to the next session without logging a completed focus
        # session or incrementing the focus session counter.
        self._change_session(completed_naturally=False)

    def skip_current_session_with_increment(self):
        """
        Immediately ends the current session and transitions to the next one,
        but still counts it as a completed focus session if it was a focus session.
        """
        # Skip but treat as naturally completed for cycle counting purposes
        self._change_session(completed_naturally=True)

    @property
    def focus_sessions_completed(self):
        """Returns the number of completed focus sessions in the current cycle."""
        return self._focus_sessions_completed

    @property
    def focus_sessions_per_cycle(self):
        """Returns how many focus sessions occur before a long break."""
        return self.FOCUS_SESSIONS_BEFORE_LONG_BREAK

    def set_cycle_length(self, focus_sessions_before_long_break):
        """
        Updates how many focus sessions are required before a long break.

        Args:
            focus_sessions_before_long_break (int): Number of focus sessions.
        """
        self.FOCUS_SESSIONS_BEFORE_LONG_BREAK = max(1, int(focus_sessions_before_long_break))

    def force_session_type(self, session_type):
        """
        Forces the timer into a specific session type ('Focus', 'Short Break', 'Long Break')
        without recording the previous session as completed.
        """
        if session_type not in ("Focus", "Short Break", "Long Break"):
            return

        # Stop any running countdown
        self.pause()

        # If we manually jump to a long break, treat it as the end of a cycle.
        if session_type == "Long Break":
            self._focus_sessions_completed = 0

        self._current_session_type = session_type
        self._set_session_duration(self._current_session_type)
        self._start_time = datetime.now()
        self.session_changed.emit(self._current_session_type)
        self.countdown_updated.emit(self._time_remaining)

    def increment_cycle_count(self):
        """Manually increment the focus session count by 1."""
        if self._focus_sessions_completed < self.FOCUS_SESSIONS_BEFORE_LONG_BREAK:
            self._focus_sessions_completed += 1

    def decrement_cycle_count(self):
        """Manually decrement the focus session count by 1."""
        if self._focus_sessions_completed > 0:
            self._focus_sessions_completed -= 1
