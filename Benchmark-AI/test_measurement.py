import unittest
from unittest.mock import Mock
from unittest.mock import patch
from pathlib import Path
import tempfile

from run import main as run_benchmark, server_execution_ms


class ServerExecutionMeasurementTests(unittest.TestCase):
    def test_uses_postgresql_execution_time(self) -> None:
        connection = Mock()
        connection.execute.return_value.fetchone.return_value = (
            [{"Plan": {"Actual Rows": 1}, "Execution Time": 2.75, "Planning Time": 9.0}],
        )

        self.assertEqual(server_execution_ms(connection, "SELECT %s", (1,)), 2.75)
        connection.execute.assert_called_once_with(
            "EXPLAIN (ANALYZE, BUFFERS, TIMING OFF, FORMAT JSON) SELECT %s", (1,)
        )

    def test_rejects_missing_result(self) -> None:
        connection = Mock()
        connection.execute.return_value.fetchone.return_value = (
            [{"Plan": {"Actual Rows": 0}, "Execution Time": 1.0}],
        )

        with self.assertRaisesRegex(RuntimeError, "exactly one row"):
            server_execution_ms(connection, "SELECT %s", (1,))

    def test_existing_results_are_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = Path(temporary) / "results.json"
            result.write_text("original")
            with patch("sys.argv", ["run.py", "--output", temporary]), \
                    patch("run.subprocess.run") as docker, self.assertRaises(SystemExit) as error:
                run_benchmark()
            self.assertEqual(error.exception.code, 2)
            self.assertEqual(result.read_text(), "original")
            docker.assert_not_called()


if __name__ == "__main__":
    unittest.main()
