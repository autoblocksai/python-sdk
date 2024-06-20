from autoblocks._impl.util import ThirdPartyEnvVar

try:
    import openai

    assert openai.__version__.startswith("1.")
except (ImportError, AssertionError):
    raise ImportError(
        "The Autoblocks evaluator requires openai version 1.x. " "You can install it with `pip install openai==1.*`."
    )


openai_api_key = ThirdPartyEnvVar.OPENAI_API_KEY.get()
if not openai_api_key:
    raise ValueError(
        f"You must set the {ThirdPartyEnvVar.OPENAI_API_KEY} environment variable to use the Autoblocks evaluator."
    )

openai_client = openai.AsyncOpenAI(api_key=openai_api_key)
