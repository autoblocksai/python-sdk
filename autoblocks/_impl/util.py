import json
import os
import subprocess
from dataclasses import asdict
from dataclasses import dataclass
from typing import Dict
from typing import List
from typing import Optional


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
class ReplayData:
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
    pull_request_number: Optional[str]
    pull_request_title: Optional[str]

    @staticmethod
    def snake_to_kebab(s: str) -> str:
        """
        Converts from snake_case to Kebab-Case. For example:

        >>> snake_to_kebab("hello_world")
        "Hello-World"
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
    return subprocess.run(cmd, stdout=subprocess.PIPE).stdout.decode("utf8")


def get_local_branch_name() -> str:
    return run_command(
        [
            "git",
            "rev-parse",
            "--abbrev-ref",
            "HEAD",
        ]
    ).strip()


def get_local_commit_data(sha: Optional[str]) -> Commit:
    log_format = "%n".join(
        [
            "sha=%H",
            "author_name=%an",
            "author_email=%ae",
            "committer_name=%cn",
            "committer_email=%ce",
            "committed_date=%aI",
            # This should be last because commit messages can contain multiple lines
            "commit_message=%B",
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
    for line in out.splitlines():
        key, value = line.split("=", maxsplit=1)

        if key == "commit_message":
            # Stop once we reach the commit message since it might consist of multiple lines
            break

        data[key] = value

    # Now get the commit message, which is everything after "commit_message="
    data["commit_message"] = out.split("commit_message=", maxsplit=1)[-1]

    return Commit(**data)


def get_replay_data() -> Optional[ReplayData]:
    if os.environ.get("GITHUB_ACTIONS"):
        # GitHub Actions
        g = {k.split("GITHUB_", maxsplit=1)[-1]: v for k, v in os.environ.items() if k.startswith("GITHUB_")}

        with open(g["EVENT_PATH"], "r") as f:
            event = json.load(f)

        commit = get_local_commit_data(g["SHA"])

        # When it's a `push` event, GITHUB_REF_NAME will have the branch name, but on
        # the `pull_request` event it will have the merge ref, like 5/merge, so for
        # pull request events we get the branch name off the webhook payload below.
        branch_name = g["REF_NAME"]

        try:
            pull_request_number = event["pull_request"]["number"]
            pull_request_title = event["pull_request"]["title"]
            branch_name = event["pull_request"]["head"]["ref"]
        except KeyError:
            pull_request_number = None
            pull_request_title = None

        return ReplayData(
            provider="github",
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
            pull_request_number=pull_request_number,
            pull_request_title=pull_request_title,
        )

    elif replay_id := os.environ.get("AUTOBLOCKS_REPLAY_ID"):
        # Local
        commit = get_local_commit_data(sha=None)
        return ReplayData(
            provider="local",
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
            pull_request_number=None,
            pull_request_title=None,
        )

    return None


def make_http_headers() -> Optional[Dict]:
    replay_data = get_replay_data()
    if replay_data:
        return replay_data.to_http_headers()
    return None


def test_headers():
    import pprint

    pprint.pprint(make_http_headers())
