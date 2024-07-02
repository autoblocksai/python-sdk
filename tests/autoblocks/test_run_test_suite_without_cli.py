import dataclasses

from autoblocks.testing.models import BaseTestCase
from autoblocks.testing.models import BaseTestEvaluator
from autoblocks.testing.models import Evaluation
from autoblocks.testing.run import run_test_suite


def test_run_test_suite_without_cli():
    @dataclasses.dataclass
    class MyTestCase(BaseTestCase):
        input: str

        def hash(self) -> str:
            return self.input

    class EvaluatorA(BaseTestEvaluator):
        id = "evaluator-a"

        def evaluate_test_case(self, test_case: MyTestCase, output: str) -> Evaluation:
            return Evaluation(score=0, metadata=dict(reason="because"))

    class EvaluatorB(BaseTestEvaluator):
        id = "evaluator-b"

        def evaluate_test_case(self, test_case: MyTestCase, output: str) -> Evaluation:
            return Evaluation(score=1)

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(input="a"),
            MyTestCase(input="b"),
        ],
        evaluators=[
            EvaluatorA(),
            EvaluatorB(),
        ],
        fn=lambda test_case: test_case.input.upper(),
        max_test_case_concurrency=1,
    )
