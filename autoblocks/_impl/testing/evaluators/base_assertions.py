import abc
import inspect
from typing import Any
from typing import Awaitable
from typing import Generic
from typing import List
from typing import Optional
from typing import Union

from autoblocks._impl.testing.models import Assertion
from autoblocks._impl.testing.models import BaseTestEvaluator
from autoblocks._impl.testing.models import Evaluation
from autoblocks._impl.testing.models import OutputType
from autoblocks._impl.testing.models import TestCaseType
from autoblocks._impl.testing.models import Threshold


class BaseAssertions(BaseTestEvaluator, abc.ABC, Generic[TestCaseType, OutputType]):
    """
    Base evaluator for creating an assertions evaluator.
    """

    @abc.abstractmethod
    def evaluate_assertions(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> Union[Optional[List[Assertion]], Awaitable[Optional[List[Assertion]]]]:
        pass

    async def evaluate_test_case(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> Optional[Evaluation]:
        """
        Evaluates the test case and returns an evaluation.
        """
        assertions_result = None
        if inspect.iscoroutinefunction(self.evaluate_assertions):
            assertions_result = await self.evaluate_assertions(*args, **kwargs)
        else:
            assertions_result = self.evaluate_assertions(*args, **kwargs)

        if assertions_result is None or len(assertions_result) == 0:
            return None

        # The evaluator passes if all required assertions pass
        passed = all(res.passed for res in assertions_result if res.required)

        return Evaluation(
            score=1 if passed else 0,
            assertions=assertions_result,
            threshold=Threshold(gte=1),
        )
