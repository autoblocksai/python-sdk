import dataclasses
import hashlib
import itertools
import traceback
from typing import Any
from typing import Generator
from typing import Optional
from typing import Sequence

import orjson

from autoblocks._impl.testing.models import BaseTestCase
from autoblocks._impl.testing.models import HumanReviewField
from autoblocks._impl.testing.models import TestCaseConfig
from autoblocks._impl.testing.models import TestCaseContext
from autoblocks._impl.testing.models import TestCaseType

# This attribute name might sound redundant, but it is named this
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
    elif isinstance(o, Exception):
        return "".join(
            traceback.format_exception(
                type(o),
                o,
                o.__traceback__,
            )
        )
    raise TypeError


def serialize(x: Any) -> Any:
    return orjson.loads(orjson.dumps(x, default=orjson_default))


def serialize_test_case(test_case: BaseTestCase) -> Any:
    obj_to_serialize = test_case.serialize()
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


def serialize_output(output: Any) -> Any:
    if callable(getattr(output, "serialize", None)):
        return serialize(output.serialize())
    return serialize(output)


def serialize_human_review_fields(fields: Optional[list[HumanReviewField]]) -> Optional[list[dict[str, str]]]:
    if fields is not None:
        return [f.serialize() for f in fields]
    return None


def serialize_test_case_for_human_review(test_case: BaseTestCase) -> Optional[list[dict[str, str]]]:
    return serialize_human_review_fields(test_case.serialize_for_human_review())


def serialize_output_for_human_review(output: Any) -> Optional[list[dict[str, str]]]:
    if callable(getattr(output, "serialize_for_human_review", None)):
        return serialize_human_review_fields(output.serialize_for_human_review())
    return None


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


GridSearchParams = dict[str, Sequence[Any]]
GridSearchParamsCombo = dict[str, Any]


def yield_grid_search_param_combos(params: GridSearchParams) -> Generator[GridSearchParamsCombo, None, None]:
    keys = list(params.keys())
    values = list(params.values())
    for combo in itertools.product(*values):
        yield dict(zip(keys, combo))
