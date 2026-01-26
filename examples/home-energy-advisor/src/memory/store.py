"""MemoryStore: JSON file-based persistence for user profiles and sessions."""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from src.core.models import UserProfile


class MemoryStore:
    """Persists user profiles and session messages to JSON files.

    Directory layout:
        data_dir/
            profiles/       # One JSON file per user
            sessions/       # One JSON file per session
    """

    STALENESS_THRESHOLD_DAYS = 90

    def __init__(self, data_dir: str | Path = "./data"):
        self.data_dir = Path(data_dir)
        self.profiles_dir = self.data_dir / "profiles"
        self.sessions_dir = self.data_dir / "sessions"

    def _ensure_dirs(self):
        """Create data directories if they don't exist."""
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _profile_path(self, user_id: str) -> Path:
        return self.profiles_dir / f"{user_id}.json"

    def _session_path(self, session_id: str) -> Path:
        return self.sessions_dir / f"{session_id}.json"

    def load_profile(self, user_id: str) -> UserProfile | None:
        """Load a user profile from disk.

        Returns None if the profile doesn't exist.
        """
        path = self._profile_path(user_id)
        if not path.exists():
            return None

        data = json.loads(path.read_text())
        return UserProfile.model_validate(data)

    def save_profile(self, profile: UserProfile) -> None:
        """Save a user profile to disk atomically.

        Uses a temporary file + rename for atomic writes.
        """
        self._ensure_dirs()
        path = self._profile_path(profile.user_id)

        data = profile.model_dump(mode="json")

        # Atomic write: write to temp file then rename
        fd, tmp_path = tempfile.mkstemp(
            dir=str(self.profiles_dir), suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2, default=str)
            os.replace(tmp_path, str(path))
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    def update_field(self, user_id: str, field_path: str, value: Any) -> None:
        """Update a single field in a user profile.

        Args:
            user_id: The user whose profile to update.
            field_path: Dotted path like "equipment.solar_capacity_kw".
            value: The new value to set.

        Raises:
            ValueError: If the user profile doesn't exist.
        """
        profile = self.load_profile(user_id)
        if profile is None:
            raise ValueError(f"Profile for user '{user_id}' not found")

        parts = field_path.split(".")
        if len(parts) == 2:
            section_name, field_name = parts
            section = getattr(profile, section_name, None)
            if section is not None:
                setattr(section, field_name, value)
                # Refresh section timestamp
                if hasattr(section, "updated_at"):
                    section.updated_at = datetime.now(tz=None)
        elif len(parts) == 1:
            setattr(profile, parts[0], value)

        profile.updated_at = datetime.now(tz=None)
        self.save_profile(profile)

    def get_field_staleness(self, user_id: str, section_name: str) -> dict:
        """Calculate staleness of a profile section.

        Args:
            user_id: The user to check.
            section_name: One of "equipment", "preferences", "household".

        Returns:
            Dict with 'days_old' (float) and 'is_stale' (bool, True if > 90 days).

        Raises:
            ValueError: If the user profile doesn't exist.
        """
        profile = self.load_profile(user_id)
        if profile is None:
            raise ValueError(f"Profile for user '{user_id}' not found")

        section = getattr(profile, section_name, None)
        if section is None or not hasattr(section, "updated_at"):
            return {"days_old": 0, "is_stale": False}

        now = datetime.now(tz=None)
        delta = now - section.updated_at
        days_old = delta.total_seconds() / 86400

        return {
            "days_old": days_old,
            "is_stale": days_old >= self.STALENESS_THRESHOLD_DAYS,
        }

    def get_session_messages(self, session_id: str) -> list[dict]:
        """Get all messages for a session.

        Returns empty list if session doesn't exist.
        """
        path = self._session_path(session_id)
        if not path.exists():
            return []

        data = json.loads(path.read_text())
        return data.get("messages", [])

    def append_message(self, session_id: str, message: dict) -> None:
        """Append a message to a session's message list."""
        self._ensure_dirs()
        path = self._session_path(session_id)

        if path.exists():
            data = json.loads(path.read_text())
        else:
            data = {"session_id": session_id, "messages": []}

        data["messages"].append(message)
        path.write_text(json.dumps(data, indent=2, default=str))

    def clear_session(self, session_id: str) -> None:
        """Remove all messages from a session."""
        path = self._session_path(session_id)
        if path.exists():
            path.unlink()
