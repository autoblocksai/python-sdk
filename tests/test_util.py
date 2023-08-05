from datetime import datetime

from autoblocks._impl.util import get_local_commit_data


def test_get_local_commit_data():
    # Run it for real against whatever commit we're on
    commit = get_local_commit_data(sha=None)

    # Do sanity checks
    assert len(commit.sha) == 40
    assert commit.commit_message
    assert commit.committer_name
    assert "@" in commit.committer_email
    assert commit.author_name
    assert "@" in commit.author_email

    # Check committed date is a valid ISO 8601 date
    datetime.fromisoformat(commit.committed_date)
