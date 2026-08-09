import unittest
from unittest.mock import patch

from resonance.device import device as device_state
from resonance.scene.scene import Scene
from resonance.solvers import boot, recovery
from resonance.utils.exceptions import StopExecution


class BootStartupTests(unittest.TestCase):
    def setUp(self):
        self.previous_stop = device_state.STOP
        device_state.STOP = False

    def tearDown(self):
        device_state.STOP = self.previous_stop

    def test_emulator_not_ready_stops_before_device_connection(self):
        with patch.object(boot, "launch_emulator", return_value=False), patch.object(
            boot, "connect"
        ) as connect:
            self.assertIsNone(boot.boot_game())
        connect.assert_not_called()

    def test_failed_game_launch_does_not_enter_recovery(self):
        with patch.object(boot, "launch_emulator", return_value=True), patch.object(
            boot, "connect", return_value=True
        ) as connect, patch.object(boot, "is_game_foreground", return_value=False), patch.object(
            boot, "start_game", return_value={"success": False}
        ), patch.object(boot, "recover_to_expected") as recover, patch.object(
            boot, "_sleep_or_stop"
        ):
            self.assertIsNone(boot.boot_game())
        self.assertEqual(connect.call_args.kwargs["reset_stop"], False)
        recover.assert_not_called()

    def test_startup_wait_is_interrupted_by_manual_stop(self):
        device_state.STOP = True
        with self.assertRaises(StopExecution):
            recovery._interruptible_sleep(1.0)

    def test_boot_recovery_uses_extended_startup_timeout(self):
        result = recovery.RecoveryResult(ok=False)
        with patch.object(boot, "launch_emulator", return_value=True), patch.object(
            boot, "connect", return_value=True
        ), patch.object(boot, "is_game_foreground", return_value=False), patch.object(
            boot, "start_game", return_value={"success": True}
        ), patch.object(boot, "recover_to_expected", return_value=result) as recover, patch.object(
            boot, "_sleep_or_stop"
        ):
            self.assertIsNone(boot.boot_game())
        context = recover.call_args.args[0]
        self.assertEqual(context.expected_scenes, {Scene.MAIN_MAP, Scene.CITY_VIEW})
        self.assertEqual(context.startup_wait_timeout, 90.0)


if __name__ == "__main__":
    unittest.main()
