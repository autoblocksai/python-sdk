<p align="center">
  <img src="https://app.autoblocks.ai/images/logo.png" width="300px">
</p>
<p align="center">
  📚
  <a href="https://docs.autoblocks.ai/">Documentation</a>
  &nbsp;
  •
  &nbsp;
  🖥️
  <a href="https://app.autoblocks.ai/">Application</a>
  &nbsp;
  •
  &nbsp;
  🏠
  <a href="https://www.autoblocks.ai/">Home</a>
</p>
<p align="center">
  <img src="assets/python-logo-only.png" width="64px">
</p>
<p align="center">
  <a href="https://github.com/autoblocksai/python-sdk/actions/workflows/ci.yml">
    <img src="https://github.com/autoblocksai/python-sdk/actions/workflows/ci.yml/badge.svg?branch=main">
  </a>
</p>

## Installation

```bash
poetry add autoblocksai
```

```bash
pip install autoblocksai
```

## Examples

See our [Python](https://github.com/autoblocksai/autoblocks-examples#python) examples.

## Quickstart

```python
import os
import uuid
import traceback
import time

import openai
from autoblocks.tracer import AutoblocksTracer

openai.api_key = os.environ["OPENAI_API_KEY"]
messages = [
  {
    "role": "system",
    "content": "You are a helpful assistant. You answer questions about a software product named Acme.",
  },
  {
    "role": "user",
    "content": "How do I sign up?",
  },
]
request_params = dict(
  model="gpt-3.5-turbo",
  messages=messages,
  temperature=0.7,
  top_p=1,
  frequency_penalty=0,
  presence_penalty=0,
  n=1,
)

tracer = AutoblocksTracer(
  os.environ["AUTOBLOCKS_INGESTION_KEY"],
  # All events sent below will have this trace ID
  trace_id=str(uuid.uuid4()),
  # All events sent below will include this property
  # alongside any other properties set in the send_event call
  properties=dict(
    provider="openai",
  ),
)

tracer.send_event(
  "ai.request",
  properties=request_params,
)

try:
  start_time = time.time()
  response = openai.ChatCompletion.create(**request_params)
  tracer.send_event(
    "ai.response",
    properties=dict(
      response=response,
      latency_ms=(time.time() - start_time) * 1000,
    ),
  )
except Exception as error:
  tracer.send_event(
    "ai.error",
    properties=dict(
      error_message=str(error),
      stacktrace=traceback.format_exc(),
    ),
  )

# Simulate user feedback
tracer.send_event(
  "user.feedback",
  properties=dict(
    feedback="good",
  ),
)
```

## Documentation

See [the full documentation](https://docs.autoblocks.ai/sdks/python).

## Issues / Questions

Please [open an issue](https://github.com/autoblocksai/python-sdk/issues/new) if you encounter any bugs, have any questions, or have any feature requests.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
