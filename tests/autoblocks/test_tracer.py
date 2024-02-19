import json
import os
import uuid
from datetime import datetime
from unittest import mock

import freezegun
import pytest
from httpx import Timeout

from autoblocks._impl.config.constants import INGESTION_ENDPOINT
from autoblocks._impl.util import encode_uri_component
from autoblocks._impl.util import get_local_branch_name
from autoblocks._impl.util import get_local_commit_data
from autoblocks.tracer import AutoblocksTracer
from tests.autoblocks.util import make_expected_body


@pytest.fixture(autouse=True)
def freeze_time():
    with freezegun.freeze_time(datetime(2021, 1, 1, 1, 1, 1, 1)):
        yield


@pytest.fixture(autouse=True)
def reset_client():
    AutoblocksTracer._client = None


timestamp = "2021-01-01T01:01:01.000001+00:00"


def test_client_init_with_key():
    tracer = AutoblocksTracer("mock-ingestion-key")
    assert tracer._client.timeout == Timeout(5)
    assert tracer._client.headers.get("authorization") == "Bearer mock-ingestion-key"


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_INGESTION_KEY": "mock-ingestion-key",
    },
)
def test_client_init_with_env_var():
    tracer = AutoblocksTracer()
    assert tracer._client.timeout == Timeout(5)
    assert tracer._client.headers.get("authorization") == "Bearer mock-ingestion-key"


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_REPLAY_ID": "replay-123",
        "GITHUB_ACTIONS": "",
    },
)
def test_tracer_local(httpx_mock):
    commit = get_local_commit_data(sha=None)
    branch = get_local_branch_name()

    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=200,
        json={"traceId": "my-trace-id"},
        match_headers={
            "Authorization": "Bearer mock-ingestion-key",
            "X-Autoblocks-Replay-Provider": encode_uri_component("local"),
            "X-Autoblocks-Replay-Run-Id": encode_uri_component("replay-123"),
            "X-Autoblocks-Replay-Branch-Name": encode_uri_component(branch),
            "X-Autoblocks-Replay-Commit-Sha": encode_uri_component(commit.sha),
            "X-Autoblocks-Replay-Commit-Message": encode_uri_component(commit.commit_message),
            "X-Autoblocks-Replay-Commit-Committer-Name": encode_uri_component(commit.committer_name),
            "X-Autoblocks-Replay-Commit-Committer-Email": encode_uri_component(commit.committer_email),
            "X-Autoblocks-Replay-Commit-Author-Name": encode_uri_component(commit.author_name),
            "X-Autoblocks-Replay-Commit-Author-Email": encode_uri_component(commit.author_email),
            "X-Autoblocks-Replay-Commit-Committed-Date": encode_uri_component(commit.committed_date),
        },
        match_content=make_expected_body(
            dict(
                message="my-message",
                traceId=None,
                timestamp=timestamp,
                properties=dict(),
            )
        ),
    )

    tracer = AutoblocksTracer("mock-ingestion-key")
    resp = tracer.send_event("my-message")
    assert resp.trace_id == "my-trace-id"


@mock.patch.dict(
    os.environ,
    {
        "GITHUB_ACTIONS": "true",
        "GITHUB_REPOSITORY": "owner/repo",
        "GITHUB_REF_NAME": "feat/branch-name",
        "GITHUB_RUN_ID": "123456789",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_SERVER_URL": "https://github.com",
    },
)
def test_tracer_ci_push(httpx_mock, tmp_path):
    # Write mock event data to a file
    with open(f"{tmp_path}/event.json", "w") as f:
        json.dump({"repository": {"default_branch": "main"}}, f)

    commit = get_local_commit_data(sha=None)

    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=200,
        json={"traceId": "my-trace-id"},
        match_headers={
            "Authorization": "Bearer mock-ingestion-key",
            "X-Autoblocks-Replay-Provider": encode_uri_component("github"),
            "X-Autoblocks-Replay-Run-Id": encode_uri_component("owner/repo-123456789-1"),
            "X-Autoblocks-Replay-Run-Url": encode_uri_component(
                "https://github.com/owner/repo/actions/runs/123456789/attempts/1"
            ),
            "X-Autoblocks-Replay-Repo": encode_uri_component("owner/repo"),
            "X-Autoblocks-Replay-Repo-Url": encode_uri_component("https://github.com/owner/repo"),
            "X-Autoblocks-Replay-Branch-Name": encode_uri_component("feat/branch-name"),
            "X-Autoblocks-Replay-Default-Branch-Name": encode_uri_component("main"),
            "X-Autoblocks-Replay-Commit-Sha": encode_uri_component(commit.sha),
            "X-Autoblocks-Replay-Commit-Message": encode_uri_component(commit.commit_message),
            "X-Autoblocks-Replay-Commit-Committer-Name": encode_uri_component(commit.committer_name),
            "X-Autoblocks-Replay-Commit-Committer-Email": encode_uri_component(commit.committer_email),
            "X-Autoblocks-Replay-Commit-Author-Name": encode_uri_component(commit.author_name),
            "X-Autoblocks-Replay-Commit-Author-Email": encode_uri_component(commit.author_email),
            "X-Autoblocks-Replay-Commit-Committed-Date": encode_uri_component(commit.committed_date),
        },
        match_content=make_expected_body(
            dict(
                message="my-message",
                traceId=None,
                timestamp=timestamp,
                properties=dict(),
            )
        ),
    )

    with mock.patch.dict(
        os.environ,
        {
            "GITHUB_EVENT_PATH": f"{tmp_path}/event.json",
            "GITHUB_SHA": commit.sha,
        },
    ):
        tracer = AutoblocksTracer("mock-ingestion-key")
        resp = tracer.send_event("my-message")

    assert resp.trace_id == "my-trace-id"


@mock.patch.dict(
    os.environ,
    {
        "GITHUB_ACTIONS": "true",
        "GITHUB_REPOSITORY": "owner/repo",
        "GITHUB_REF_NAME": "5/merge",
        "GITHUB_RUN_ID": "123456789",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_SERVER_URL": "https://github.com",
    },
)
def test_tracer_ci_pull_request(httpx_mock, tmp_path):
    # Write mock event data to a file
    with open(f"{tmp_path}/event.json", "w") as f:
        json.dump(
            {
                "repository": {"default_branch": "main"},
                "pull_request": {"number": 5, "title": "My PR Title", "head": {"ref": "my-pr-branch-name"}},
            },
            f,
        )

    commit = get_local_commit_data(sha=None)

    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=200,
        json={"traceId": "my-trace-id"},
        match_headers={
            "Authorization": "Bearer mock-ingestion-key",
            "X-Autoblocks-Replay-Provider": encode_uri_component("github"),
            "X-Autoblocks-Replay-Run-Id": encode_uri_component("owner/repo-123456789-1"),
            "X-Autoblocks-Replay-Run-Url": encode_uri_component(
                "https://github.com/owner/repo/actions/runs/123456789/attempts/1"
            ),
            "X-Autoblocks-Replay-Repo": encode_uri_component("owner/repo"),
            "X-Autoblocks-Replay-Repo-Url": encode_uri_component("https://github.com/owner/repo"),
            "X-Autoblocks-Replay-Branch-Name": encode_uri_component("my-pr-branch-name"),
            "X-Autoblocks-Replay-Default-Branch-Name": encode_uri_component("main"),
            "X-Autoblocks-Replay-Commit-Sha": encode_uri_component(commit.sha),
            "X-Autoblocks-Replay-Commit-Message": encode_uri_component(commit.commit_message),
            "X-Autoblocks-Replay-Commit-Committer-Name": encode_uri_component(commit.committer_name),
            "X-Autoblocks-Replay-Commit-Committer-Email": encode_uri_component(commit.committer_email),
            "X-Autoblocks-Replay-Commit-Author-Name": encode_uri_component(commit.author_name),
            "X-Autoblocks-Replay-Commit-Author-Email": encode_uri_component(commit.author_email),
            "X-Autoblocks-Replay-Commit-Committed-Date": encode_uri_component(commit.committed_date),
            "X-Autoblocks-Replay-Pull-Request-Number": encode_uri_component("5"),
            "X-Autoblocks-Replay-Pull-Request-Title": encode_uri_component("My PR Title"),
        },
        match_content=make_expected_body(
            dict(
                message="my-message",
                traceId=None,
                timestamp=timestamp,
                properties=dict(),
            )
        ),
    )

    with mock.patch.dict(
        os.environ,
        {
            "GITHUB_EVENT_PATH": f"{tmp_path}/event.json",
            "GITHUB_SHA": commit.sha,
        },
    ):
        tracer = AutoblocksTracer("mock-ingestion-key")
        resp = tracer.send_event("my-message")

    assert resp.trace_id == "my-trace-id"


@mock.patch.dict(
    os.environ,
    {
        "GITHUB_ACTIONS": "",
    },
)
def test_tracer_prod(httpx_mock):
    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=200,
        json={"traceId": "my-trace-id"},
        match_headers={"Authorization": "Bearer mock-ingestion-key"},
        match_content=make_expected_body(
            dict(
                message="my-message",
                traceId=None,
                timestamp=timestamp,
                properties=dict(),
            )
        ),
    )
    tracer = AutoblocksTracer("mock-ingestion-key")
    resp = tracer.send_event("my-message")

    assert resp.trace_id == "my-trace-id"


@mock.patch.dict(
    os.environ,
    {
        "GITHUB_ACTIONS": "",
    },
)
def test_tracer_prod_no_trace_id_in_response(httpx_mock):
    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=200,
        json={},
        match_headers={"Authorization": "Bearer mock-ingestion-key"},
        match_content=make_expected_body(
            dict(
                message="my-message",
                traceId=None,
                timestamp=timestamp,
                properties=dict(),
            )
        ),
    )
    tracer = AutoblocksTracer("mock-ingestion-key")
    resp = tracer.send_event("my-message")

    assert resp.trace_id is None


@mock.patch.dict(
    os.environ,
    {
        "GITHUB_ACTIONS": "",
    },
)
def test_tracer_prod_with_trace_id_in_send_event(httpx_mock):
    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=200,
        json={},
        match_headers={"Authorization": "Bearer mock-ingestion-key"},
        match_content=make_expected_body(
            dict(
                message="my-message",
                traceId="my-trace-id",
                timestamp=timestamp,
                properties=dict(),
            )
        ),
    )

    tracer = AutoblocksTracer("mock-ingestion-key")
    tracer.send_event("my-message", trace_id="my-trace-id")


@mock.patch.dict(
    os.environ,
    {
        "GITHUB_ACTIONS": "",
    },
)
def test_tracer_prod_with_trace_id_in_init(httpx_mock):
    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=200,
        json={},
        match_headers={"Authorization": "Bearer mock-ingestion-key"},
        match_content=make_expected_body(
            dict(
                message="my-message",
                traceId="my-trace-id",
                timestamp=timestamp,
                properties=dict(),
            )
        ),
    )
    tracer = AutoblocksTracer("mock-ingestion-key", trace_id="my-trace-id")
    tracer.send_event("my-message")


@mock.patch.dict(
    os.environ,
    {
        "GITHUB_ACTIONS": "",
    },
)
def test_tracer_prod_with_trace_id_override(httpx_mock):
    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=200,
        json={},
        match_headers={"Authorization": "Bearer mock-ingestion-key"},
        match_content=make_expected_body(
            dict(
                message="my-message",
                traceId="override-trace-id",
                timestamp=timestamp,
                properties=dict(),
            )
        ),
    )

    tracer = AutoblocksTracer("mock-ingestion-key", trace_id="my-trace-id")
    tracer.send_event("my-message", trace_id="override-trace-id")


@mock.patch.dict(
    os.environ,
    {
        "GITHUB_ACTIONS": "",
    },
)
def test_tracer_prod_with_set_trace_id(httpx_mock):
    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=200,
        json={},
        match_headers={"Authorization": "Bearer mock-ingestion-key"},
        match_content=make_expected_body(
            dict(
                message="my-message",
                traceId="override-trace-id",
                timestamp=timestamp,
                properties=dict(),
            )
        ),
    )

    tracer = AutoblocksTracer("mock-ingestion-key", trace_id="my-trace-id")
    tracer.set_trace_id("override-trace-id")
    tracer.send_event("my-message")


@mock.patch.dict(
    os.environ,
    {
        "GITHUB_ACTIONS": "",
    },
)
def test_tracer_prod_with_properties(httpx_mock):
    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=200,
        json={},
        match_headers={"Authorization": "Bearer mock-ingestion-key"},
        match_content=make_expected_body(
            dict(
                message="my-message",
                traceId=None,
                timestamp=timestamp,
                properties=dict(x=1),
            )
        ),
    )

    tracer = AutoblocksTracer("mock-ingestion-key", properties=dict(x=1))
    tracer.send_event("my-message")


@mock.patch.dict(
    os.environ,
    {
        "GITHUB_ACTIONS": "",
    },
)
def test_tracer_prod_with_set_properties(httpx_mock):
    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=200,
        json={},
        match_headers={"Authorization": "Bearer mock-ingestion-key"},
        match_content=make_expected_body(
            dict(
                message="my-message",
                traceId=None,
                timestamp=timestamp,
                properties=dict(y=2),
            )
        ),
    )

    tracer = AutoblocksTracer("mock-ingestion-key", properties=dict(x=1))
    tracer.set_properties(dict(y=2))
    tracer.send_event("my-message")


@mock.patch.dict(
    os.environ,
    {
        "GITHUB_ACTIONS": "",
    },
)
def test_tracer_prod_with_update_properties(httpx_mock):
    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=200,
        json={},
        match_headers={"Authorization": "Bearer mock-ingestion-key"},
        match_content=make_expected_body(
            dict(
                message="my-message",
                traceId=None,
                timestamp=timestamp,
                properties=dict(x=1, y=2),
            )
        ),
    )

    tracer = AutoblocksTracer("mock-ingestion-key", properties=dict(x=1))
    tracer.update_properties(dict(y=2))
    tracer.send_event("my-message")


@mock.patch.dict(
    os.environ,
    {
        "GITHUB_ACTIONS": "",
    },
)
def test_tracer_prod_with_update_properties_and_send_event_properties(httpx_mock):
    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=200,
        json={},
        match_headers={"Authorization": "Bearer mock-ingestion-key"},
        match_content=make_expected_body(
            dict(
                message="my-message",
                traceId=None,
                timestamp=timestamp,
                properties=dict(x=1, y=2, z=3),
            )
        ),
    )

    tracer = AutoblocksTracer("mock-ingestion-key", properties=dict(x=1))
    tracer.update_properties(dict(y=2))
    tracer.send_event("my-message", properties=dict(z=3))


@mock.patch.dict(
    os.environ,
    {
        "GITHUB_ACTIONS": "",
    },
)
def test_tracer_prod_with_properties_with_conflicting_keys(httpx_mock):
    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=200,
        json={},
        match_headers={"Authorization": "Bearer mock-ingestion-key"},
        match_content=make_expected_body(
            dict(
                message="my-message",
                traceId=None,
                timestamp=timestamp,
                properties=dict(x=3, y=2, z=3),
            )
        ),
    )

    tracer = AutoblocksTracer("mock-ingestion-key", properties=dict(x=1))
    tracer.update_properties(dict(y=2))
    tracer.send_event("my-message", properties=dict(x=3, z=3))


@mock.patch.dict(
    os.environ,
    {
        "GITHUB_ACTIONS": "",
    },
)
def test_tracer_prod_with_timestamp(httpx_mock):
    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=200,
        json={},
        match_headers={"Authorization": "Bearer mock-ingestion-key"},
        match_content=make_expected_body(
            dict(
                message="my-message",
                traceId=None,
                timestamp="2023-07-24T21:52:52.742Z",
                properties=dict(),
            )
        ),
    )

    tracer = AutoblocksTracer("mock-ingestion-key")
    tracer.send_event("my-message", timestamp="2023-07-24T21:52:52.742Z")


def test_tracer_prod_swallows_errors(httpx_mock):
    httpx_mock.add_exception(Exception())

    tracer = AutoblocksTracer("mock-ingestion-key")
    resp = tracer.send_event("my-message")
    assert resp.trace_id is None


@mock.patch.dict(
    os.environ,
    dict(AUTOBLOCKS_TRACER_THROW_ON_ERROR="1"),
)
def test_tracer_prod_throws_errors_when_configured(httpx_mock):
    class MyCustomException(Exception):
        pass

    httpx_mock.add_exception(MyCustomException())

    tracer = AutoblocksTracer("mock-ingestion-key")
    with pytest.raises(MyCustomException):
        tracer.send_event("my-message")


@mock.patch.dict(
    os.environ,
    {
        "GITHUB_ACTIONS": "",
    },
)
def test_tracer_prod_handles_non_200(httpx_mock):
    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=400,
        json={},
        match_headers={"Authorization": "Bearer mock-ingestion-key"},
        match_content=make_expected_body(
            dict(
                message="my-message",
                traceId=None,
                timestamp=timestamp,
                properties=dict(),
            )
        ),
    )

    tracer = AutoblocksTracer("mock-ingestion-key")
    resp = tracer.send_event("my-message")
    assert resp.trace_id is None


@mock.patch.dict(
    os.environ,
    {
        "GITHUB_ACTIONS": "",
    },
)
def test_tracer_sends_span_id_as_property(httpx_mock):
    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=200,
        json={"traceId": "my-trace-id"},
        match_headers={"Authorization": "Bearer mock-ingestion-key"},
        match_content=make_expected_body(
            dict(
                message="my-message",
                traceId=None,
                timestamp=timestamp,
                properties=dict(span_id="my-span-id"),
            )
        ),
    )
    tracer = AutoblocksTracer("mock-ingestion-key")
    resp = tracer.send_event("my-message", span_id="my-span-id")

    assert resp.trace_id == "my-trace-id"


@mock.patch.dict(
    os.environ,
    {
        "GITHUB_ACTIONS": "",
    },
)
def test_tracer_sends_parent_span_id_as_property(httpx_mock):
    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=200,
        json={"traceId": "my-trace-id"},
        match_headers={"Authorization": "Bearer mock-ingestion-key"},
        match_content=make_expected_body(
            dict(
                message="my-message",
                traceId=None,
                timestamp=timestamp,
                properties=dict(parent_span_id="my-parent-span-id"),
            )
        ),
    )
    tracer = AutoblocksTracer("mock-ingestion-key")
    resp = tracer.send_event("my-message", parent_span_id="my-parent-span-id")

    assert resp.trace_id == "my-trace-id"


@mock.patch.dict(
    os.environ,
    {
        "GITHUB_ACTIONS": "",
    },
)
def test_tracer_sends_span_id_and_parent_span_id_as_property(httpx_mock):
    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=200,
        json={"traceId": "my-trace-id"},
        match_headers={"Authorization": "Bearer mock-ingestion-key"},
        match_content=make_expected_body(
            dict(
                message="my-message",
                traceId=None,
                timestamp=timestamp,
                properties=dict(span_id="my-span-id", parent_span_id="my-parent-span-id"),
            )
        ),
    )
    tracer = AutoblocksTracer("mock-ingestion-key")
    resp = tracer.send_event("my-message", span_id="my-span-id", parent_span_id="my-parent-span-id")

    assert resp.trace_id == "my-trace-id"


@mock.patch.dict(
    os.environ,
    {
        "GITHUB_ACTIONS": "",
        "AUTOBLOCKS_INGESTION_KEY": "key",
    },
)
@mock.patch.object(
    uuid,
    "uuid4",
    side_effect=[f"mock-uuid-{i}" for i in range(10)],
)
def test_tracer_start_span(*args, **kwargs):
    tracer = AutoblocksTracer()

    assert tracer._properties.get("span_id") is None
    assert tracer._properties.get("parent_span_id") is None

    with tracer.start_span():
        assert tracer._properties["span_id"] == "mock-uuid-0"
        assert tracer._properties.get("parent_span_id") is None

        with tracer.start_span():
            assert tracer._properties["span_id"] == "mock-uuid-1"
            assert tracer._properties["parent_span_id"] == "mock-uuid-0"

            with tracer.start_span():
                assert tracer._properties["span_id"] == "mock-uuid-2"
                assert tracer._properties["parent_span_id"] == "mock-uuid-1"

        with tracer.start_span():
            assert tracer._properties["span_id"] == "mock-uuid-3"
            assert tracer._properties["parent_span_id"] == "mock-uuid-0"

        assert tracer._properties["span_id"] == "mock-uuid-0"
        assert tracer._properties.get("parent_span_id") is None

    assert tracer._properties.get("span_id") is None
    assert tracer._properties.get("parent_span_id") is None


@mock.patch.dict(
    os.environ,
    {
        "GITHUB_ACTIONS": "",
        "AUTOBLOCKS_INGESTION_KEY": "key",
    },
)
def test_tracer_single_client():
    tracer1 = AutoblocksTracer()
    assert tracer1._client is not None
    tracer2 = AutoblocksTracer()
    assert tracer2._client is tracer1._client
    assert id(tracer2._client) == id(tracer1._client)
