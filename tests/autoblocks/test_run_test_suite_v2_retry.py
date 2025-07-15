import dataclasses
import os
from unittest import mock

import httpx
import pytest

from autoblocks._impl.util import AutoblocksEnvVar
from autoblocks.testing.models import BaseTestCase
from autoblocks.testing.models import BaseTestEvaluator
from autoblocks.testing.models import Evaluation
from autoblocks.testing.v2.run import run_test_suite
from autoblocks.tracer import init_auto_tracer


@dataclasses.dataclass
class MyTestCase(BaseTestCase):
    input: str

    def hash(self) -> str:
        return self.input


class MyEvaluator(BaseTestEvaluator):
    id = "my-evaluator"

    def evaluate_test_case(self, test_case: MyTestCase, output: str) -> Evaluation:
        return Evaluation(score=1.0, metadata=dict(output=output))


@pytest.fixture(autouse=True)
def mock_env_vars():
    """Mock environment variables needed for V2 testing."""
    with mock.patch.dict(
        os.environ,
        {
            AutoblocksEnvVar.V2_API_KEY.value: "mock-api-key",
        },
    ):
        yield


@pytest.fixture(autouse=True)
def init_tracer():
    """Initialize auto tracer for V2 tests."""
    init_auto_tracer(
        api_key="mock-api-key",
    )


def test_v2_retry_on_timeout_errors():
    """Test that retry_count parameter retries test cases on timeout/connection errors in V2."""

    # Mock the test function to fail twice then succeed
    call_count = 0

    def test_fn(test_case: MyTestCase) -> str:
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            # First two calls fail with timeout
            raise httpx.TimeoutException("Request timed out")
        return test_case.input + "!"

    run_test_suite(
        id="my-test-id",
        app_slug="test-app",
        test_cases=[
            MyTestCase(input="a"),
        ],
        evaluators=[],
        fn=test_fn,
        max_test_case_concurrency=1,
        retry_count=3,  # Allow up to 3 retries
    )

    # Should have been called 3 times (2 failures + 1 success)
    assert call_count == 3


def test_v2_retry_exhausted_logs_error():
    """Test that when retries are exhausted, the error is properly logged in V2."""

    # Mock the test function to always fail with timeout
    call_count = 0

    def test_fn(test_case: MyTestCase) -> str:
        nonlocal call_count
        call_count += 1
        raise httpx.TimeoutException("Request timed out")

    run_test_suite(
        id="my-test-id",
        app_slug="test-app",
        test_cases=[
            MyTestCase(input="a"),
        ],
        evaluators=[],
        fn=test_fn,
        max_test_case_concurrency=1,
        retry_count=2,  # Allow up to 2 retries
    )

    # Should have been called 3 times (2 retries + 1 original attempt)
    assert call_count == 3


def test_v2_retry_only_on_specific_exceptions():
    """Test that retry only happens for specific httpx exceptions, not all exceptions in V2."""

    # Mock the test function to fail with ValueError (should not retry)
    call_count = 0

    def test_fn(test_case: MyTestCase) -> str:
        nonlocal call_count
        call_count += 1
        raise ValueError("Not a timeout error")

    run_test_suite(
        id="my-test-id",
        app_slug="test-app",
        test_cases=[
            MyTestCase(input="a"),
        ],
        evaluators=[],
        fn=test_fn,
        max_test_case_concurrency=1,
        retry_count=3,  # Allow up to 3 retries
    )

    # Should have been called only once (no retries for ValueError)
    assert call_count == 1


def test_v2_retry_count_zero_no_retry():
    """Test that retry_count=0 (default) doesn't retry on timeout errors in V2."""

    # Mock the test function to fail with timeout
    call_count = 0

    def test_fn(test_case: MyTestCase) -> str:
        nonlocal call_count
        call_count += 1
        raise httpx.TimeoutException("Request timed out")

    run_test_suite(
        id="my-test-id",
        app_slug="test-app",
        test_cases=[
            MyTestCase(input="a"),
        ],
        evaluators=[],
        fn=test_fn,
        max_test_case_concurrency=1,
        retry_count=0,  # No retries
    )

    # Should have been called only once (no retries)
    assert call_count == 1


def test_v2_retry_with_evaluators():
    """Test that retry works correctly with evaluators in V2."""

    # Mock the test function to fail once then succeed
    call_count = 0

    def test_fn(test_case: MyTestCase) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First call fails with timeout
            raise httpx.TimeoutException("Request timed out")
        return test_case.input + "!"

    run_test_suite(
        id="my-test-id",
        app_slug="test-app",
        test_cases=[
            MyTestCase(input="a"),
        ],
        evaluators=[MyEvaluator()],
        fn=test_fn,
        max_test_case_concurrency=1,
        retry_count=2,  # Allow up to 2 retries
    )

    # Should have been called 2 times (1 failure + 1 success)
    assert call_count == 2


def test_v2_retry_with_connection_errors():
    """Test that retry works with different types of connection errors in V2."""

    # Test different types of connection errors
    error_types = [
        httpx.ConnectError("Connection failed"),
        httpx.ReadTimeout("Read timeout"),
        httpx.WriteTimeout("Write timeout"),
        httpx.PoolTimeout("Pool timeout"),
    ]

    for error_type in error_types:
        call_count = 0

        def test_fn(test_case: MyTestCase) -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call fails with the specific error
                raise error_type
            return test_case.input + "!"

        run_test_suite(
            id="my-test-id",
            app_slug="test-app",
            test_cases=[
                MyTestCase(input="a"),
            ],
            evaluators=[],
            fn=test_fn,
            max_test_case_concurrency=1,
            retry_count=1,  # Allow 1 retry
        )

        # Should have been called 2 times (1 failure + 1 success)
        assert call_count == 2


def test_v2_retry_with_async_function():
    """Test that retry works with async test functions in V2."""

    # Mock the async test function to fail once then succeed
    call_count = 0

    async def async_test_fn(test_case: MyTestCase) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First call fails with timeout
            raise httpx.TimeoutException("Request timed out")
        return test_case.input + "!"

    run_test_suite(
        id="my-test-id",
        app_slug="test-app",
        test_cases=[
            MyTestCase(input="a"),
        ],
        evaluators=[],
        fn=async_test_fn,
        max_test_case_concurrency=1,
        retry_count=2,  # Allow up to 2 retries
    )

    # Should have been called 2 times (1 failure + 1 success)
    assert call_count == 2
