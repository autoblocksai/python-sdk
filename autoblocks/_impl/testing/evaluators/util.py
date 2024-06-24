from autoblocks._impl.context_vars import test_case_run_context_var
from autoblocks._impl.util import AutoblocksEnvVar
from autoblocks._impl.util import ThirdPartyEnvVar


# Wrapped in a function so that the error is only thrown when relevant evaluators are used
def get_openai_client(evaluator_id: str):  # type: ignore[no-untyped-def]
    try:
        import openai

        assert openai.__version__.startswith("1.")
    except (ImportError, AssertionError):
        raise ImportError(
            f"The {evaluator_id} evaluator requires openai version 1.x. "
            "You can install it with `pip install openai==1.*`."
        )

    openai_api_key = ThirdPartyEnvVar.OPENAI_API_KEY.get()
    if not openai_api_key:
        raise ValueError(
            f"You must set the {ThirdPartyEnvVar.OPENAI_API_KEY} environment variable. "
            f"When using the {evaluator_id} evaluator."
        )

    return openai.AsyncOpenAI(api_key=openai_api_key)


# Wrapped in a function so that the error is only thrown when relevant evaluators are used
def get_autoblocks_api_key(evaluator_id: str) -> str:
    autoblocks_api_key = AutoblocksEnvVar.API_KEY.get()
    # The Autoblocks API key should always be set since we will be in a testing context
    if not autoblocks_api_key:
        raise ValueError(
            f"You must set the {AutoblocksEnvVar.API_KEY} environment variable to use the {evaluator_id} evaluator."
        )

    return autoblocks_api_key


def get_test_id(evaluator_id: str) -> str:
    """
    Retrieves the current test from the test run context
    """
    test_run_ctx = test_case_run_context_var.get()
    if test_run_ctx is None:
        # Evaluators should always be run inside the context of a test case
        raise ValueError(f"No test case context found in the {evaluator_id} evaluator.")
    return test_run_ctx.test_id
