from datetime import datetime
from unittest import mock

from autoblocks._impl.util import encode_uri_component
from autoblocks._impl.util import get_local_branch_name
from autoblocks._impl.util import get_local_commit_data
from autoblocks._impl.util import get_local_repo_name
from autoblocks._impl.util import parse_repo_name_from_origin_url


def test_get_local_commit_data_real():
    # Run it for real against whatever commit we're on
    commit = get_local_commit_data(sha=None)

    # Do sanity checks
    assert len(commit.sha) == 40
    assert commit.commit_message
    assert "\n" not in commit.commit_message
    assert commit.committer_name
    assert "@" in commit.committer_email
    assert commit.author_name
    assert "@" in commit.author_email

    # Check committed date is a valid ISO 8601 date
    datetime.fromisoformat(commit.committed_date)


def test_get_local_commit_data_mocked():
    # Test get_local_commit_data while mocking run_command
    with mock.patch("autoblocks._impl.util.run_command") as run_command:
        run_command.return_value = (
            "sha=3567334251119b2457a0d4b8996b431491aa8a41\n"
            "author_name=Nicole=White\n"
            "author_email=nicole@autoblocks.ai\n"
            "committer_name=commit_message=Nicole White\n"
            "committer_email=nicole@autoblocks.ai\n"
            "committed_date=2023-08-05T18:48:50-04:00\n"
            "commit_message=Line 1\nLine 2\nLine 3"
        )
        commit = get_local_commit_data(sha=None)

    assert commit.sha == "3567334251119b2457a0d4b8996b431491aa8a41"
    assert commit.author_name == "Nicole=White"
    assert commit.author_email == "nicole@autoblocks.ai"
    assert commit.committer_name == "commit_message=Nicole White"
    assert commit.committer_email == "nicole@autoblocks.ai"
    assert commit.committed_date == "2023-08-05T18:48:50-04:00"
    assert commit.commit_message == "Line 1"


def test_get_local_repo_name():
    assert get_local_repo_name() == "autoblocksai/python-sdk"


def test_get_local_branch_name():
    assert get_local_branch_name()


def test_encode_uri_component():
    assert encode_uri_component("hello") == "hello"
    assert encode_uri_component("hello world") == "hello%20world"
    assert encode_uri_component("hello\n!().*'") == "hello%0A!().*'"


def test_parse_https_github():
    assert (
        parse_repo_name_from_origin_url("https://github.com/autoblocksai/neon-actions.git")
        == "autoblocksai/neon-actions"
    )


def test_parse_https_gitlab():
    assert (
        parse_repo_name_from_origin_url("https://gitlab.com/gitlab-com/www-gitlab-com.git")
        == "gitlab-com/www-gitlab-com"
    )


def test_parse_ssh_github():
    assert (
        parse_repo_name_from_origin_url("git@github.com:autoblocksai/neon-actions.git") == "autoblocksai/neon-actions"
    )


def test_parse_ssh_gitlab():
    assert (
        parse_repo_name_from_origin_url("git@gitlab.com:gitlab-com/www-gitlab-com.git") == "gitlab-com/www-gitlab-com"
    )
