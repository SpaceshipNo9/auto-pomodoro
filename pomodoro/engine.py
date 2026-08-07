from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Phase(str, Enum):
    WAITING = "waiting"
    WORKING = "working"
    WORK_ALERT = "work_alert"
    RESTING = "resting"
    READY_ALERT = "ready_alert"


class Event(str, Enum):
    NONE = "none"
    WORK_STARTED = "work_started"
    IDLE_RESET = "idle_reset"
    WORK_FINISHED = "work_finished"
    REST_STARTED = "rest_started"
    REST_FINISHED = "rest_finished"
    CYCLE_RESET = "cycle_reset"


@dataclass
class Durations:
    work_seconds: float = 25 * 60
    idle_seconds: float = 3 * 60
    rest_seconds: float = 5 * 60


class PomodoroEngine:
    """UI-independent state machine driven by a monotonic clock."""

    def __init__(self, durations: Durations) -> None:
        self.durations = durations
        self.phase = Phase.WAITING
        self.deadline: float | None = None
        self.last_mouse_move: float | None = None

    def reset(self) -> Event:
        self.phase = Phase.WAITING
        self.deadline = None
        self.last_mouse_move = None
        return Event.CYCLE_RESET

    def mouse_moved(self, now: float) -> Event:
        if self.phase is Phase.WAITING:
            self.phase = Phase.WORKING
            self.deadline = now + self.durations.work_seconds
            self.last_mouse_move = now
            return Event.WORK_STARTED
        if self.phase is Phase.WORKING:
            self.last_mouse_move = now
        return Event.NONE

    def tick(self, now: float) -> Event:
        if self.phase is Phase.WORKING:
            if (
                self.last_mouse_move is not None
                and now - self.last_mouse_move >= self.durations.idle_seconds
            ):
                self.reset()
                return Event.IDLE_RESET
            if self.deadline is not None and now >= self.deadline:
                self.phase = Phase.WORK_ALERT
                self.deadline = None
                return Event.WORK_FINISHED

        if self.phase is Phase.RESTING and self.deadline is not None and now >= self.deadline:
            self.phase = Phase.READY_ALERT
            self.deadline = None
            return Event.REST_FINISHED

        return Event.NONE

    def confirm_work_alert(self, now: float) -> Event:
        if self.phase is not Phase.WORK_ALERT:
            return Event.NONE
        self.phase = Phase.RESTING
        self.deadline = now + self.durations.rest_seconds
        self.last_mouse_move = None
        return Event.REST_STARTED

    def confirm_ready_alert(self) -> Event:
        if self.phase is not Phase.READY_ALERT:
            return Event.NONE
        self.reset()
        return Event.CYCLE_RESET

    def remaining_seconds(self, now: float) -> int | None:
        if self.deadline is None:
            return None
        return max(0, int(self.deadline - now + 0.999))
