"""Performance tests for CUID2 validation."""

import time

import pytest
from cuid2 import cuid_wrapper

from autoblocks._impl.util import is_valid_cuid2


@pytest.fixture
def valid_cuid2():
    """Generate a valid CUID2 for testing."""
    return cuid_wrapper()()


def test_cuid2_validation_performance(valid_cuid2):
    """Ensure CUID2 validation doesn't become a bottleneck."""
    # Test with valid CUID2
    start = time.perf_counter()

    for _ in range(10000):
        is_valid_cuid2(valid_cuid2)

    duration = time.perf_counter() - start

    # Should validate 10k CUIDs in less than 100ms
    assert duration < 0.1, f"Validation too slow: {duration:.3f}s for 10k validations"

    # Log performance for visibility
    print(f"Performance: {10000/duration:.0f} validations/second")


def test_cuid2_validation_performance_invalid():
    """Test performance with invalid CUID2s."""
    invalid_samples = [
        "abc123",  # too short
        "abc123def456ghi789jkl012extra",  # too long
        "ABC123def456ghi789jkl012",  # uppercase
        "abc123def456ghi789jkl-12",  # special chars
        "",  # empty
    ]

    start = time.perf_counter()

    for _ in range(2000):  # 2k iterations per sample = 10k total
        for invalid_cuid in invalid_samples:
            is_valid_cuid2(invalid_cuid)

    duration = time.perf_counter() - start

    # Should validate 10k invalid CUIDs in less than 100ms
    assert duration < 0.1, f"Invalid validation too slow: {duration:.3f}s for 10k validations"

    # Log performance for visibility
    print(f"Invalid performance: {10000/duration:.0f} validations/second")


def test_cuid2_validation_mixed_performance(valid_cuid2):
    """Test performance with mixed valid/invalid CUID2s."""
    test_cases = [
        valid_cuid2,
        "abc123",  # invalid
        valid_cuid2,
        "ABC123def456ghi789jkl012",  # invalid
        valid_cuid2,
    ]

    start = time.perf_counter()

    for _ in range(2000):  # 2k iterations * 5 cases = 10k total
        for test_case in test_cases:
            is_valid_cuid2(test_case)

    duration = time.perf_counter() - start

    # Should validate 10k mixed CUIDs in less than 100ms
    assert duration < 0.1, f"Mixed validation too slow: {duration:.3f}s for 10k validations"

    # Log performance for visibility
    print(f"Mixed performance: {10000/duration:.0f} validations/second")
