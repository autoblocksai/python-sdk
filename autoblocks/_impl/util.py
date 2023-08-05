import json
import os
import subprocess
from collections import deque
from dataclasses import asdict
from dataclasses import dataclass
from enum import Enum
from typing import Dict
from typing import List
from typing import Optional


class Provider(str, Enum):
    LOCAL = "local"
    GITHUB = "github"

    def __str__(self) -> str:
        # https://stackoverflow.com/a/74440069
        return str.__str__(self)


@dataclass(frozen=True)
class Commit:
    sha: str
    author_name: str
    author_email: str
    committer_name: str
    committer_email: str
    committed_date: str
    commit_message: str


@dataclass(frozen=True)
class ReplayRun:
    provider: str
    run_id: str
    run_url: Optional[str]
    repo: Optional[str]
    repo_url: Optional[str]
    branch_name: str
    default_branch_name: Optional[str]
    commit_sha: str
    commit_message: str
    commit_committer_name: str
    commit_committer_email: str
    commit_author_name: str
    commit_author_email: str
    commit_committed_date: str
    pull_request_number: Optional[str]
    pull_request_title: Optional[str]

    @staticmethod
    def snake_to_kebab(s: str) -> str:
        """
        Converts from snake_case to Kebab-Case. For example:

        "hello_world" -> "Hello-World"
        """
        return "-".join([x[0].upper() + x[1:] for x in s.split("_")])

    def to_http_headers(self) -> Dict[str, str]:
        d = asdict(self)
        headers = {}
        for k, v in d.items():
            if v is None:
                continue
            headers[f"X-Autoblocks-Replay-{self.snake_to_kebab(k)}"] = str(v).strip()
        return headers


def run_command(cmd: List[str]) -> str:
    return subprocess.run(cmd, stdout=subprocess.PIPE).stdout.decode("utf8").strip()


def get_local_branch_name() -> str:
    return run_command(
        [
            "git",
            "rev-parse",
            "--abbrev-ref",
            "HEAD",
        ]
    )


def get_local_commit_data(sha: Optional[str]) -> Commit:
    commit_message_key = "commit_message"

    log_format = "%n".join(
        [
            "sha=%H",
            "author_name=%an",
            "author_email=%ae",
            "committer_name=%cn",
            "committer_email=%ce",
            "committed_date=%aI",
            # This should be last because commit messages can contain multiple lines
            f"{commit_message_key}=%B",
        ]
    )
    out = run_command(
        [
            "git",
            "show",
            sha or "HEAD",
            "--quiet",
            f"--format={log_format}",
        ]
    )

    data = {}
    lines = deque(out.splitlines())
    while lines:
        line = lines.popleft()
        key, value = line.split("=", maxsplit=1)

        if key == commit_message_key:
            # Once we've reached the commit message key, the remaining lines are the commit message
            data[commit_message_key] = "\n".join([value, *lines])
            break

        data[key] = value

    return Commit(**data)


def make_replay_run() -> Optional[ReplayRun]:
    if os.environ.get("GITHUB_ACTIONS"):
        # GitHub Actions
        g = {k.split("GITHUB_", maxsplit=1)[-1]: v for k, v in os.environ.items() if k.startswith("GITHUB_")}

        with open(g["EVENT_PATH"], "r") as f:
            # GitHub Actions are triggered by webhook events, and the event payload is
            # stored in a JSON file at $GITHUB_EVENT_PATH.
            # You can see the schema of the various webhook payloads at:
            # https://docs.github.com/en/webhooks-and-events/webhooks/webhook-events-and-payloads
            event = json.load(f)

        commit = get_local_commit_data(g["SHA"])

        try:
            pull_request_number = event["pull_request"]["number"]
            pull_request_title = event["pull_request"]["title"]
            branch_name = event["pull_request"]["head"]["ref"]
        except KeyError:
            pull_request_number = None
            pull_request_title = None
            # When it's a `push` event, GITHUB_REF_NAME will have the branch name, but on
            # the `pull_request` event it will have the merge ref, like 5/merge, so for
            # pull request events we get the branch name off the webhook payload above.
            branch_name = g["REF_NAME"]

        return ReplayRun(
            provider=Provider.GITHUB,
            run_id=f"{g['REPOSITORY']}-{g['RUN_ID']}-{g['RUN_ATTEMPT']}",
            run_url="/".join(
                [
                    g["SERVER_URL"],
                    g["REPOSITORY"],
                    "actions",
                    "runs",
                    g["RUN_ID"],
                    "attempts",
                    g["RUN_ATTEMPT"],
                ]
            ),
            repo=g["REPOSITORY"],
            repo_url="/".join(
                [
                    g["SERVER_URL"],
                    g["REPOSITORY"],
                ]
            ),
            branch_name=branch_name,
            default_branch_name=event["repository"]["default_branch"],
            commit_sha=commit.sha,
            commit_message=commit.commit_message,
            commit_committer_name=commit.committer_name,
            commit_committer_email=commit.committer_email,
            commit_author_name=commit.author_name,
            commit_author_email=commit.author_email,
            commit_committed_date=commit.committed_date,
            pull_request_number=pull_request_number,
            pull_request_title=pull_request_title,
        )

    elif replay_id := os.environ.get("AUTOBLOCKS_REPLAY_ID"):
        # Local
        commit = get_local_commit_data(sha=None)
        return ReplayRun(
            provider=Provider.LOCAL,
            run_id=replay_id,
            run_url=None,
            repo=None,
            repo_url=None,
            branch_name=get_local_branch_name(),
            default_branch_name=None,
            commit_sha=commit.sha,
            commit_message=commit.commit_message,
            commit_committer_name=commit.committer_name,
            commit_committer_email=commit.committer_email,
            commit_author_name=commit.author_name,
            commit_author_email=commit.author_email,
            commit_committed_date=commit.committed_date,
            pull_request_number=None,
            pull_request_title=None,
        )

    return None


def make_replay_headers() -> Optional[Dict]:
    replay_run = make_replay_run()
    if replay_run:
        return replay_run.to_http_headers()
    return None
