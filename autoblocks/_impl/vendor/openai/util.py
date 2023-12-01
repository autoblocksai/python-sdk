import json


def serialize_completion(completion):
    # openai v0 returns a dictionary and openai v1 returns a ChatCompletion or Completion
    # pydantic BaseModel
    if hasattr(completion, "model_dump_json") and callable(completion.model_dump_json):
        # Pydantic v2
        return json.loads(completion.model_dump_json())
    elif hasattr(completion, "json") and callable(completion.json):
        # Pydantic v1
        return json.loads(completion.json())
    return completion
