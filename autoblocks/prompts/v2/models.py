from typing import Any, Dict, List, Optional, Union

try:
    import pydantic
    assert pydantic.__version__.startswith("2.")
except (ImportError, AssertionError):
    raise ImportError(
        "The Autoblocks prompt SDK requires pydantic version 2.x. "
        "You can install it with `pip install pydantic==2.*`."
    )


class FrozenModel(pydantic.BaseModel):
    """Base model with frozen attributes for V2 prompts."""
    model_config = pydantic.ConfigDict(frozen=True)


class WeightedMinorVersion(FrozenModel):
    """Weighted minor version for A/B testing."""
    version: str
    weight: float = pydantic.Field(..., gt=0) 