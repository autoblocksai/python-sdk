import os
import signal
import subprocess
import time
import uuid

from autoblocks._impl.api.client import AutoblocksAPIClient

client = AutoblocksAPIClient()


def test_tracer_received_sigint_or_sigterm():
    test_trace_id = uuid.uuid4()
    # Start the main.py script as a subprocess
    process = subprocess.Popen(
        ["python", "tests/e2e/tracer_shutdown/tracer_shutdown_test_process.py", str(test_trace_id)]
    )
    time.sleep(1)

    os.kill(process.pid, signal.SIGINT)

    # Wait for the process to terminate
    process.wait()
    time.sleep(4)  # give a moment for autoblocks to
    test = client.get_trace(str(test_trace_id))
    # Assert that the process has terminated successfully
    assert test is not None
