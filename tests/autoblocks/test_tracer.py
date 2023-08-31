import json
import os
from unittest import mock

from autoblocks._impl.config.constants import INGESTION_ENDPOINT
from autoblocks._impl.util import encode_uri_component
from autoblocks._impl.util import get_local_branch_name
from autoblocks._impl.util import get_local_commit_data
from autoblocks.tracer import AutoblocksTracer
from tests.autoblocks.util import make_expected_body


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_SIMULATION_ID": "replay-123",
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
                timestamp=None,
                properties=dict(),
            )
        ),
    )

    ab = AutoblocksTracer("mock-ingestion-key")
    resp = ab.send_event("my-message")
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
                timestamp=None,
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
        ab = AutoblocksTracer("mock-ingestion-key")
        resp = ab.send_event("my-message")

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
                timestamp=None,
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
        ab = AutoblocksTracer("mock-ingestion-key")
        resp = ab.send_event("my-message")

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
                timestamp=None,
                properties=dict(),
            )
        ),
    )
    ab = AutoblocksTracer("mock-ingestion-key")
    resp = ab.send_event("my-message")

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
                timestamp=None,
                properties=dict(),
            )
        ),
    )
    ab = AutoblocksTracer("mock-ingestion-key")
    resp = ab.send_event("my-message")

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
                timestamp=None,
                properties=dict(),
            )
        ),
    )

    ab = AutoblocksTracer("mock-ingestion-key")
    ab.send_event("my-message", trace_id="my-trace-id")


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
                timestamp=None,
                properties=dict(),
            )
        ),
    )
    ab = AutoblocksTracer("mock-ingestion-key", trace_id="my-trace-id")
    ab.send_event("my-message")


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
                timestamp=None,
                properties=dict(),
            )
        ),
    )

    ab = AutoblocksTracer("mock-ingestion-key", trace_id="my-trace-id")
    ab.send_event("my-message", trace_id="override-trace-id")


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
                timestamp=None,
                properties=dict(),
            )
        ),
    )

    ab = AutoblocksTracer("mock-ingestion-key", trace_id="my-trace-id")
    ab.set_trace_id("override-trace-id")
    ab.send_event("my-message")


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
                timestamp=None,
                properties=dict(x=1),
            )
        ),
    )

    ab = AutoblocksTracer("mock-ingestion-key", properties=dict(x=1))
    ab.send_event("my-message")


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
                timestamp=None,
                properties=dict(y=2),
            )
        ),
    )

    ab = AutoblocksTracer("mock-ingestion-key", properties=dict(x=1))
    ab.set_properties(dict(y=2))
    ab.send_event("my-message")


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
                timestamp=None,
                properties=dict(x=1, y=2),
            )
        ),
    )

    ab = AutoblocksTracer("mock-ingestion-key", properties=dict(x=1))
    ab.update_properties(dict(y=2))
    ab.send_event("my-message")


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
                timestamp=None,
                properties=dict(x=1, y=2, z=3),
            )
        ),
    )

    ab = AutoblocksTracer("mock-ingestion-key", properties=dict(x=1))
    ab.update_properties(dict(y=2))
    ab.send_event("my-message", properties=dict(z=3))


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
                timestamp=None,
                properties=dict(x=3, y=2, z=3),
            )
        ),
    )

    ab = AutoblocksTracer("mock-ingestion-key", properties=dict(x=1))
    ab.update_properties(dict(y=2))
    ab.send_event("my-message", properties=dict(x=3, z=3))


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

    ab = AutoblocksTracer("mock-ingestion-key")
    ab.send_event("my-message", timestamp="2023-07-24T21:52:52.742Z")


def test_tracer_prod_catches_errors(httpx_mock):
    httpx_mock.add_exception(Exception())

    ab = AutoblocksTracer("mock-ingestion-key")
    resp = ab.send_event("my-message")
    assert resp.trace_id is None


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
                timestamp=None,
                properties=dict(),
            )
        ),
    )

    ab = AutoblocksTracer("mock-ingestion-key")
    resp = ab.send_event("my-message")
    assert resp.trace_id is None
