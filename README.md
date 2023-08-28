<p align="center">
  <img src="https://app.autoblocks.ai/images/logo.png" width="300px">
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

## Quickstart

```python
from autoblocks.tracer import AutoblocksTracer

tracer = AutoblocksTracer("my-ingestion-key")
tracer.send_event("my-first-event")
```

## Documentation

See [the full documentation](https://docs.autoblocks.ai/sdks/python).

## Issues / Questions

Please [open an issue](https://github.com/autoblocksai/python-sdk/issues/new) if you encounter any bugs, have any questions, or have any feature requests.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
