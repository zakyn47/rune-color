"""Ask the RuneLite client for the selected script's profile, through the bridge."""

import threading
import time
from typing import Any, Callable, Optional, Protocol

from model.bot import Bot
from utilities import runelite_profiles


class ProfileBridge(Protocol):
    """The part of `BridgeAPI` that profiles need, so tests can stand in for it."""

    @property
    def active_profile(self) -> Optional[str]:
        """Optional[str]: The client's active profile, or None if unknown."""

    def request_profile(self, name: str, path: str) -> None:
        """Ask for a profile by name, imported from the file at `path`."""

    def clear_profile(self) -> None:
        """Stop asking for a profile."""


class ProfileSelector:
    """Decides which RuneLite profile to ask for, and reports whether it took."""

    def __init__(
        self,
        bridge: ProfileBridge,
        get_setting: Callable[[str], Any],
        set_setting: Callable[[str, Any], None],
        log: Callable[[str], None],
        confirm_timeout: float = 10,
        poll: float = 0.5,
    ) -> None:
        """Instantiate a `ProfileSelector`.

        Args:
            bridge (ProfileBridge): The shared `BridgeAPI`.
            get_setting (Callable[[str], Any]): Reads a persisted setting.
            set_setting (Callable[[str, Any], None]): Persists a setting.
            log (Callable[[str], None]): Writes a line to the UI's log.
            confirm_timeout (float, optional): Seconds to wait for the client to
                switch before warning. Defaults to 10.
            poll (float, optional): Seconds between checks. Defaults to 0.5.
        """
        self._bridge = bridge
        self._get = get_setting
        self._set = set_setting
        self._log = log
        self._timeout = confirm_timeout
        self._poll = poll
        self._model: Optional[Bot] = None
        self._requested: Optional[str] = None

    @property
    def use_own(self) -> bool:
        """bool: Whether the user keeps their own RuneLite profile."""
        return bool(self._get(runelite_profiles.USE_OWN_PROFILE_SETTING))

    def set_use_own(self, value: bool) -> None:
        """Remember the user's choice and apply it to the selected script.

        Args:
            value (bool): True to keep the user's own profile.
        """
        self._set(runelite_profiles.USE_OWN_PROFILE_SETTING, value)
        self.select(self._model)

    def select(self, model: Optional[Bot]) -> None:
        """Ask for the profile of the newly selected script, or for none.

        Args:
            model (Optional[Bot]): The selected script, or None.
        """
        self._model = model
        key = getattr(model, "runelite_profile", None)
        if self.use_own or key is None:
            self._requested = None
            self._bridge.clear_profile()
            return
        name = runelite_profiles.profile_name(model.bot_title)
        self._requested = name
        self._bridge.request_profile(name, str(runelite_profiles.profile_path(key)))
        threading.Thread(target=self._confirm, args=(name,), daemon=True).start()

    def _confirm(self, name: str) -> None:
        deadline = time.time() + self._timeout
        while time.time() < deadline:
            if self._requested != name:
                return  # Another script was selected meanwhile.
            if self._bridge.active_profile == name:
                self._log(f"Switched RuneLite to profile {name}.")
                return
            time.sleep(self._poll)
        if self._requested == name:
            self._log(
                f"RuneLite didn't switch to profile {name} within"
                f" {self._timeout:g} s. Is the RuneColor Bridge plug-in on?"
            )
