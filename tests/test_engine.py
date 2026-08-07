import unittest

from pomodoro.engine import Durations, Event, Phase, PomodoroEngine


class PomodoroEngineTests(unittest.TestCase):
    @staticmethod
    def make_engine() -> PomodoroEngine:
        return PomodoroEngine(Durations(work_seconds=10, idle_seconds=3, rest_seconds=5))

    def test_mouse_movement_starts_work(self) -> None:
        engine = self.make_engine()
        self.assertIs(engine.mouse_moved(100), Event.WORK_STARTED)
        self.assertIs(engine.phase, Phase.WORKING)
        self.assertEqual(engine.remaining_seconds(100), 10)

    def test_idle_mouse_resets_work_cycle(self) -> None:
        engine = self.make_engine()
        engine.mouse_moved(100)
        engine.mouse_moved(102)
        self.assertIs(engine.tick(104.9), Event.NONE)
        self.assertIs(engine.tick(105), Event.IDLE_RESET)
        self.assertIs(engine.phase, Phase.WAITING)

    def test_complete_cycle_requires_both_confirmations(self) -> None:
        engine = self.make_engine()
        engine.mouse_moved(100)
        engine.mouse_moved(109)
        self.assertIs(engine.tick(110), Event.WORK_FINISHED)
        self.assertIs(engine.phase, Phase.WORK_ALERT)
        self.assertIs(engine.confirm_work_alert(120), Event.REST_STARTED)
        self.assertEqual(engine.remaining_seconds(120), 5)
        self.assertIs(engine.tick(125), Event.REST_FINISHED)
        self.assertIs(engine.phase, Phase.READY_ALERT)
        self.assertIs(engine.confirm_ready_alert(), Event.CYCLE_RESET)
        self.assertIs(engine.phase, Phase.WAITING)

    def test_mouse_is_ignored_during_rest(self) -> None:
        engine = self.make_engine()
        engine.mouse_moved(0)
        engine.mouse_moved(9)
        engine.tick(10)
        engine.confirm_work_alert(20)
        self.assertIs(engine.mouse_moved(22), Event.NONE)
        self.assertIs(engine.phase, Phase.RESTING)


if __name__ == "__main__":
    unittest.main()
