import unittest
from unittest.mock import patch

from flask import Flask

from resonance.device import device as device_state
from resonance.scheduler.models import Task, TaskStatus
from resonance.scheduler.scheduler import Scheduler
from resonance.server.app import app as flask_app
from resonance.server.routes.business import business_bp
from resonance.server.routes.device import device_bp
from resonance.solvers.trade import TradeRouteSolver
from resonance.utils.exceptions import TaskExecutionFailed


class BusinessRouteValidationTests(unittest.TestCase):
    def setUp(self):
        self.app = flask_app
        self.app.testing = True
        if "business" not in self.app.blueprints:
            self.app.register_blueprint(business_bp, url_prefix="/api/business")
        self.client = self.app.test_client()

    def test_start_rejects_unknown_city_before_scheduling(self):
        response = self.client.post(
            "/api/business/start",
            json={"cities": ["不存在的城市", "另一不存在的城市"]},
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["success"])
        self.assertIn("城市名称无效", response.get_json()["error"])


class DeviceRouteTests(unittest.TestCase):
    def setUp(self):
        # Use an isolated app because Flask disallows blueprint registration
        # after another test has served its first request on the shared app.
        self.app = Flask(__name__)
        self.app.testing = True
        self.app.register_blueprint(device_bp, url_prefix="/api/device")
        self.client = self.app.test_client()

    def test_status_uses_explicit_connection_state(self):
        with patch("resonance.server.routes.device.is_connected", return_value=False):
            response = self.client.get("/api/device/status")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.get_json()["connected"])
        self.assertIsNone(response.get_json()["actual_method"])

    def test_disconnect_endpoint_clears_connection(self):
        with patch("resonance.server.routes.device.disconnect", return_value=True) as disconnect:
            response = self.client.post("/api/device/disconnect")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["success"])
        self.assertFalse(response.get_json()["connected"])
        disconnect.assert_called_once()


class TaskFailureTests(unittest.TestCase):
    def setUp(self):
        self.previous_stop = device_state.STOP

    def tearDown(self):
        device_state.STOP = self.previous_stop

    def test_trade_failure_is_not_reported_as_completion(self):
        solver = TradeRouteSolver(cities=["A", "B"])
        solver.routes = object()
        with patch.object(solver, "ensure_connected", return_value="A"), patch.object(
            solver, "_normalize_takeover_city", return_value="A"
        ), patch.object(solver, "_run_one_round", return_value=None), patch.object(
            solver, "_execute_on_stop_action"
        ), patch("resonance.solvers.trade.app.RunBuy.BuyCount", 1
        ):
            with self.assertRaises(TaskExecutionFailed):
                solver._transition_locked()

    def test_scheduler_marks_terminal_business_failure_as_failed(self):
        class FailingSolver:
            def run(self):
                raise TaskExecutionFailed("expected failure")

        scheduler = Scheduler()
        task = Task(
            solver_path="test.FailingSolver",
            name="failing task",
        )
        scheduler._tasks[task.solver_path] = task
        scheduler._priority_queue.append(task)
        scheduler._running = True

        with patch.object(scheduler, "_import_solver", return_value=FailingSolver):
            scheduler._tick()

        self.assertEqual(task.status, TaskStatus.FAILED)
        self.assertFalse(task.enabled)


if __name__ == "__main__":
    unittest.main()
