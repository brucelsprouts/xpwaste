
import json
import os
from datetime import datetime

class SessionHistoryManager:
    """
    Manages the loading, saving, and retrieval of XP Waste session data from a JSON file.
    Handles individual session entries and overall history, including calculating total study time for the day.
    """

    def __init__(self, history_file='data/session_history.json'):
        """
        Initializes the SessionHistoryManager with the path to the history file.

        Args:
            history_file (str): The path to the JSON file where session history is stored.
                                  Defaults to 'data/session_history.json'.
        """
        self.history_file = history_file
        self.history = self.load_history()

    def load_history(self):
        """
        Loads session history from the JSON file.

        Returns:
            list: A list of session dictionaries. Returns an empty list if the file
                  does not exist or is empty, or if there's a JSON decoding error.
        """
        if not os.path.exists(self.history_file):
            return []

        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content:
                    return []
                data = json.loads(content)
                # Ensure we always return a list, even if an older version
                # of the file stored a dict or another structure.
                if isinstance(data, list):
                    return data
                if isinstance(data, dict):
                    maybe_list = data.get("history", [])
                    if isinstance(maybe_list, list):
                        return maybe_list
                    return []
                return []
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from {self.history_file}. Initializing with empty history.")
            return []
        except Exception as e:
            print(f"An unexpected error occurred while loading history: {e}")
            return []

    def save_history(self):
        """
        Saves the current session history to the JSON file.
        """
        try:
            os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=4)
        except IOError as e:
            print(f"Error: Could not write to history file {self.history_file}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred while saving history: {e}")

    def add_session(self, session_data):
        """
        Adds a new session dictionary to the history list.

        Args:
            session_data (dict): A dictionary containing session details with keys:
                                 'date' (str), 'start_time' (str), 'end_time' (str),
                                 and 'duration' (int).
        """
        self.history.append(session_data)
        self.save_history()

    def remove_session_at(self, index):
        """Removes a session at index if valid and persists the updated history."""
        if index < 0 or index >= len(self.history):
            return False
        del self.history[index]
        self.save_history()
        return True

    def get_history(self):
        """
        Returns the entire list of recorded sessions.

        Returns:
            list: A list of all recorded session dictionaries.
        """
        return self.history

    def get_total_study_time_today(self):
        """
        Calculates and returns the sum of 'duration' for all sessions recorded on the current date.

        Returns:
            int: The total study time in minutes for the current day.
        """
        today = datetime.now().strftime('%Y-%m-%d')
        total_duration = 0
        for session in self.history:
            if session.get('date') == today:
                total_duration += session.get('duration', 0)
        return total_duration

    @staticmethod
    def _session_active_seconds(session):
        """Returns active study seconds with backward compatibility for old entries."""
        if "active_seconds" in session:
            try:
                return max(0, int(session.get("active_seconds", 0)))
            except (TypeError, ValueError):
                return 0
        try:
            return max(0, int(session.get("duration", 0)) * 60)
        except (TypeError, ValueError):
            return 0

    def get_total_study_seconds_today(self):
        """Returns total active study seconds for today's sessions."""
        today = datetime.now().strftime('%Y-%m-%d')
        return sum(
            self._session_active_seconds(session)
            for session in self.history
            if session.get('date') == today
        )

    def get_focus_session_count_today(self):
        """Returns the number of focus sessions recorded today."""
        today = datetime.now().strftime('%Y-%m-%d')
        return sum(
            1 for session in self.history
            if session.get('date') == today and session.get('session_type') == 'Focus'
        )

    def get_total_study_seconds_overall(self):
        """Returns total active study seconds across all sessions."""
        return sum(self._session_active_seconds(session) for session in self.history)
