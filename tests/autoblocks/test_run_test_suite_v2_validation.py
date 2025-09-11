import dataclasses
import os
import re
from unittest import mock

import pytest
from cuid2 import cuid_wrapper

from autoblocks._impl.util import AutoblocksEnvVar
from autoblocks.testing.models import BaseTestCase
from autoblocks.testing.models import BaseTestEvaluator
from autoblocks.testing.models import Evaluation
from autoblocks.testing.v2.run import run_test_suite
from autoblocks.tracer import init_auto_tracer

# Test data constants
VALID_CUID2_SAMPLE = "abc123def456ghi789jkl012"
INVALID_CUID2_SAMPLES = {
    "too_short": "abc123",
    "too_long": "abc123def456ghi789jkl012extra",
    "uppercase": "ABC123def456ghi789jkl012",
    "special_chars": "abc123def456ghi789jkl-12",
    "empty": "",
}


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


@pytest.fixture
def valid_cuid2():
    """Generate a valid CUID2 for testing."""
    return cuid_wrapper()()


@pytest.fixture
def test_function():
    """Standard test function for validation tests."""

    def test_fn(test_case: MyTestCase) -> str:
        return test_case.input + "!"

    return test_fn


def test_v2_run_id_validation_valid_cuid2(test_function):
    """Test that run_test_suite accepts valid CUID2 run_id."""
    # Should not raise an exception
    run_test_suite(
        id="my-test-id",
        app_slug="test-app",
        test_cases=[
            MyTestCase(input="a"),
        ],
        fn=test_function,
        evaluators=[],
        run_id=VALID_CUID2_SAMPLE,
    )


def test_v2_run_id_validation_invalid_cuid2_too_short(test_function):
    """Test that run_test_suite raises ValueError for CUID2 that's too short."""
    invalid_run_id = INVALID_CUID2_SAMPLES["too_short"]

    with pytest.raises(ValueError, match=f"Invalid run_id: '{invalid_run_id}'. Must be a valid CUID2."):
        run_test_suite(
            id="my-test-id",
            app_slug="test-app",
            test_cases=[
                MyTestCase(input="a"),
            ],
            fn=test_function,
            evaluators=[],
            run_id=invalid_run_id,
        )


def test_v2_run_id_validation_invalid_cuid2_too_long():
    """Test that run_test_suite raises ValueError for CUID2 that's too long."""

    def test_fn(test_case: MyTestCase) -> str:
        return test_case.input + "!"

    # Invalid CUID2 - too long
    invalid_run_id = "abc123def456ghi789jkl012extra"

    with pytest.raises(ValueError, match="Invalid run_id: 'abc123def456ghi789jkl012extra'. Must be a valid CUID2."):
        run_test_suite(
            id="my-test-id",
            app_slug="test-app",
            test_cases=[
                MyTestCase(input="a"),
            ],
            fn=test_fn,
            evaluators=[],
            run_id=invalid_run_id,
        )


def test_v2_run_id_validation_invalid_cuid2_uppercase():
    """Test that run_test_suite raises ValueError for CUID2 with uppercase letters."""

    def test_fn(test_case: MyTestCase) -> str:
        return test_case.input + "!"

    # Invalid CUID2 - contains uppercase letters
    invalid_run_id = "ABC123def456ghi789jkl012"

    with pytest.raises(ValueError, match="Invalid run_id: 'ABC123def456ghi789jkl012'. Must be a valid CUID2."):
        run_test_suite(
            id="my-test-id",
            app_slug="test-app",
            test_cases=[
                MyTestCase(input="a"),
            ],
            fn=test_fn,
            evaluators=[],
            run_id=invalid_run_id,
        )


def test_v2_run_id_validation_invalid_cuid2_special_chars():
    """Test that run_test_suite raises ValueError for CUID2 with special characters."""

    def test_fn(test_case: MyTestCase) -> str:
        return test_case.input + "!"

    # Invalid CUID2 - contains special characters
    invalid_run_id = "abc123def456ghi789jkl-12"

    with pytest.raises(ValueError, match="Invalid run_id: 'abc123def456ghi789jkl-12'. Must be a valid CUID2."):
        run_test_suite(
            id="my-test-id",
            app_slug="test-app",
            test_cases=[
                MyTestCase(input="a"),
            ],
            fn=test_fn,
            evaluators=[],
            run_id=invalid_run_id,
        )


def test_v2_run_id_validation_none_run_id_auto_generates():
    """Test that run_test_suite works with None run_id (auto-generation)."""

    def test_fn(test_case: MyTestCase) -> str:
        return test_case.input + "!"

    # Should not raise an exception and auto-generate a run_id
    run_test_suite(
        id="my-test-id",
        app_slug="test-app",
        test_cases=[
            MyTestCase(input="a"),
        ],
        fn=test_fn,
        evaluators=[],
        run_id=None,  # Should auto-generate
    )


def test_v2_run_id_validation_empty_string(test_function):
    """Test that run_test_suite raises ValueError for empty string run_id."""
    invalid_run_id = INVALID_CUID2_SAMPLES["empty"]

    with pytest.raises(ValueError, match=f"Invalid run_id: '{invalid_run_id}'. Must be a valid CUID2."):
        run_test_suite(
            id="my-test-id",
            app_slug="test-app",
            test_cases=[
                MyTestCase(input="a"),
            ],
            fn=test_function,
            evaluators=[],
            run_id=invalid_run_id,
        )


@pytest.mark.parametrize("invalid_case", list(INVALID_CUID2_SAMPLES.keys()))
def test_v2_run_id_validation_parametrized_invalid_cases(test_function, invalid_case):
    """Parametrized test for all invalid CUID2 cases."""
    invalid_run_id = INVALID_CUID2_SAMPLES[invalid_case]

    with pytest.raises(ValueError, match=f"Invalid run_id: '{re.escape(invalid_run_id)}'. Must be a valid CUID2."):
        run_test_suite(
            id="my-test-id",
            app_slug="test-app",
            test_cases=[
                MyTestCase(input="a"),
            ],
            fn=test_function,
            evaluators=[],
            run_id=invalid_run_id,
        )


def test_v2_run_id_validation_with_evaluators():
    """Test that run_id validation works correctly when evaluators are present."""

    def test_fn(test_case: MyTestCase) -> str:
        return test_case.input + "!"

    # Valid CUID2
    valid_run_id = "abc123def456ghi789jkl012"

    # Should not raise an exception even with evaluators
    run_test_suite(
        id="my-test-id",
        app_slug="test-app",
        test_cases=[
            MyTestCase(input="a"),
        ],
        fn=test_fn,
        evaluators=[MyEvaluator()],
        run_id=valid_run_id,
    )


def test_v2_run_id_validation_with_retry_count():
    """Test that run_id validation works correctly with retry_count parameter."""

    def test_fn(test_case: MyTestCase) -> str:
        return test_case.input + "!"

    # Valid CUID2
    valid_run_id = "abc123def456ghi789jkl012"

    # Should not raise an exception even with retry_count
    run_test_suite(
        id="my-test-id",
        app_slug="test-app",
        test_cases=[
            MyTestCase(input="a"),
        ],
        fn=test_fn,
        evaluators=[],
        run_id=valid_run_id,
        retry_count=2,
    )


def test_v2_run_id_validation_happens_after_tracer_check():
    """Test that run_id validation happens after tracer initialization check."""

    def test_fn(test_case: MyTestCase) -> str:
        return test_case.input + "!"

    # Invalid CUID2
    invalid_run_id = "invalid"

    # Mock the auto tracer to not be initialized
    with mock.patch("autoblocks._impl.global_state.is_auto_tracer_initialized", return_value=False):
        # Should return early due to tracer not being initialized, not raise ValueError
        # This tests that the function returns gracefully when tracer is not initialized
        run_test_suite(
            id="my-test-id",
            app_slug="test-app",
            test_cases=[
                MyTestCase(input="a"),
            ],
            fn=test_fn,
            evaluators=[],
            run_id=invalid_run_id,
        )
        # If we get here without exception, the tracer check happened first
