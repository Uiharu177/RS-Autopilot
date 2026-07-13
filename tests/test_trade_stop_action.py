import unittest
from unittest.mock import patch

from resonance.device import device as device_state
from resonance.solvers import recovery
from resonance.solvers.trade import TradeRouteSolver


class TradeStopActionTests(unittest.TestCase):
    def setUp(self):
        self.previous_stop = device_state.STOP

    def tearDown(self):
        device_state.STOP = self.previous_stop

    def test_goto_main_temporarily_clears_stop_and_restores_it(self):
        calls: list[bool] = []

        def safe_go_home() -> bool:
            calls.append(device_state.STOP)
            return True

        device_state.STOP = True
        solver = TradeRouteSolver()

        with patch.object(recovery, "safe_go_home", side_effect=safe_go_home):
            solver._execute_action("goto_main")

        self.assertEqual(calls, [False])
        self.assertTrue(device_state.STOP)

    def test_goto_main_restores_stop_when_returning_home_fails(self):
        device_state.STOP = True
        solver = TradeRouteSolver()

        with patch.object(recovery, "safe_go_home", side_effect=RuntimeError("failed")):
            with self.assertRaisesRegex(RuntimeError, "failed"):
                solver._execute_action("goto_main")

        self.assertTrue(device_state.STOP)

    def test_fatigue_action_executes_once_before_configured_stop_action(self):
        device_state.STOP = True
        solver = TradeRouteSolver()
        solver._fatigue_action = "goto_main"

        with patch.object(solver, "ensure_connected", return_value="city"), patch.object(
            solver, "_execute_action"
        ) as execute_action, patch.object(solver, "_execute_on_stop_action") as execute_on_stop_action:
            result = solver._run_page_flow_locked()

        self.assertTrue(result)
        execute_action.assert_called_once_with("goto_main")
        execute_on_stop_action.assert_not_called()
        self.assertIsNone(solver._fatigue_action)
