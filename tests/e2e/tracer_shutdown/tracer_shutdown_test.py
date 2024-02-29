import os
import signal
import subprocess
import time
import unittest
import uuid

from autoblocks._impl.api.client import AutoblocksAPIClient

client = AutoblocksAPIClient()


class TestMainScript(unittest.TestCase):
    def test_tracer_received_sigint_or_sigterm(self):
        test_trace_id = uuid.uuid4()
        # Start the main.py script as a subprocess
        process = subprocess.Popen(["python", "tests/e2e/tracer_shutdown/main.py", str(test_trace_id)])
        time.sleep(1)

        # Send SIGTERM to terminate the process
        os.kill(process.pid, signal.SIGTERM)

        # Wait for the process to terminate
        process.wait(timeout=15)

        test = client.get_trace(str(test_trace_id))
        # Assert that the process has terminated successfully
        self.assertIsNotNone(test)


if __name__ == "__main__":
    unittest.main()
