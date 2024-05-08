import dataclasses
import hashlib
from typing import Any
from typing import Generator
from typing import Optional
from typing import Sequence

import orjson

from autoblocks._impl.testing.models import BaseTestCase
from autoblocks._impl.testing.models import TestCaseConfig
from autoblocks._impl.testing.models import TestCaseContext
from autoblocks._impl.testing.models import TestCaseType

# This attribute name might sound redundant but it is named this
# way (as opposed to just `config`) to decrease the likelihood
# our config attr name conflicts with the name of an attr the user
# wants to use on their test case.
TEST_CASE_CONFIG_ATTR = "test_case_config"


def md5(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


def orjson_default(o: Any) -> Any:
    if hasattr(o, "model_dump_json") and callable(o.model_dump_json):
        # pydantic v2
        return orjson.loads(o.model_dump_json())
    elif hasattr(o, "json") and callable(o.json):
        # pydantic v1
        return orjson.loads(o.json())
    raise TypeError


def serialize(x: Any) -> Any:
    return orjson.loads(orjson.dumps(x, default=orjson_default))


def serialize_test_case(test_case: BaseTestCase) -> Any:
    obj_to_serialize = test_case.pre_serialization_hook()

    # See https://docs.python.org/3/library/dataclasses.html#dataclasses.is_dataclass:
    # isinstance(test_case, type) checks test_case is an instance and not a type
    if dataclasses.is_dataclass(obj_to_serialize) and not isinstance(obj_to_serialize, type):
        serialized: dict[Any, Any] = {}
        for k, v in dataclasses.asdict(obj_to_serialize).items():
            if k == TEST_CASE_CONFIG_ATTR:
                # Don't serialize the config
                continue
            try:
                serialized[k] = serialize(v)
            except Exception:
                # Skip over non-serializable test case attributes
                pass
        return serialized

    return serialize(obj_to_serialize)


def config_from_test_case(test_case: TestCaseType) -> Optional[TestCaseConfig]:
    config = getattr(test_case, TEST_CASE_CONFIG_ATTR, None)
    if isinstance(config, TestCaseConfig):
        return config
    return None


def yield_test_case_contexts_from_test_cases(
    test_cases: Sequence[TestCaseType],
) -> Generator[TestCaseContext[TestCaseType], None, None]:
    for test_case in test_cases:
        config = config_from_test_case(test_case)
        if not config or config.repeat_num_times is None:
            yield TestCaseContext(
                test_case=test_case,
                repetition_idx=None,
            )
        else:
            for idx in range(config.repeat_num_times):
                yield TestCaseContext(
                    test_case=test_case,
                    repetition_idx=idx,
                )
