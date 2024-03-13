# Contributing

## Setup

* Install [`pyenv`](https://github.com/pyenv/pyenv)
  * Install python 3.11: `pyenv install 3.11`
* Install [`pyenv-virtualenv`](https://github.com/pyenv/pyenv-virtualenv)
* Install [`poetry`](https://python-poetry.org/docs/#installation)
* Install `poetry-relax`:
  * `poetry self add poetry-relax`
* Create a virtualenv: `pyenv virtualenv 3.11 python-sdk`
  * Activate the virtualenv: `pyenv activate python-sdk`
* Install dependencies: `poetry install`
* Run tests: `poetry run pytest`
* Install pre-commit: `poetry run pre-commit install`

## Supported Python Versions

We support all versions of Python that are not yet at end-of-life: https://devguide.python.org/versions

As new versions become available they should be added to our test matrix in [`.github/workflows/ci.yaml`](./.github/workflows/ci.yml):

```yaml
strategy:
  matrix:
    python-version:
      - "3.9"
      - "3.10"
      - "3.11"
      - "3.12"
```

As versions are deprecated they should be removed from the test matrix and the minimum Python version in [`pyproject.toml`](./pyproject.toml) should be updated.

## Folder Structure

**All implementations should be in the `_impl/` folder.**

The **only** code in public folders (i.e. folders that are not the `_impl/` folder) should be re-exports of code in the `_impl/` folder.

For example, the `_impl/tracer.py` file contains the implementation of the `AutoblocksTracer` class.
This class is part of the public interface of the SDK, so it is re-exported in the `tracer.py` file:

```python
from autoblocks._impl.tracer import AutoblocksTracer  # noqa: F401
```

### Why?

This allows us to control the functions and classes end users are allowed to import.
For example, if we were to move the implementation of `AutoblocksTracer` directly into the public `tracer.py` file,
end users would be able to import all sorts of internal-only functions and classes:

```python
from autoblocks.tracer import log  # Users could import our logger!
from autoblocks.tracer import some_internal_function  # Users could import our internal functions!
```

By explicitly exporting only a subset of the code in the `_impl/` folder,
we can ensure that we don't accidentally expose any internal functions or classes that we don't want end users to use.

While it's technically possible for an end user to import from the `_impl/` folder:

```python
from autoblocks._impl.tracer import some_internal_function
```

This is not supported and we do not make any guarantees about backwards compatability for anything in the `_impl/` folder.
Most Python users will be familiar with the leading underscore as a convention for private functions and classes,
so the name of the import should be enough to discourage most users from importing from the `_impl/` folder.

## Dependencies

In general, we should try to use as few dependencies as possible in this package.
This makes it less likely our internal dependencies will conflict with the dependencies of the end user.
For example, while it might be nice to use the `pydantic` package, this is a popular package where end users might be using a different version of the package than we are.
This would force us to write complicated if-else logic like:

```python
import pydantic

version = tuple(int(i) for i in pydantic.__version__.split('.'))

if version < (2, 0, 0):
    # Code that works with pydantic v1
else:
    # Code that works with pydantic v2
```

This would greatly increase the complexity of our code, so we should avoid it if possible.

## Dependency Pinning in [`pyproject.toml`](./pyproject.toml)

The dependencies in the `[tool.poetry.dependencies]` section in `pyproject.toml` should be **as relaxed as possible**.
See https://github.com/zanieb/poetry-relax for a detailed explanation.

The dependencies in the `[tool.poetry.group.dev.dependencies]` are internal to us and can be pinned as appropriate.
