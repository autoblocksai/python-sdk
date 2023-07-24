import os
from dataclasses import dataclass
from dataclasses import field


@dataclass
class Env:
    # `CI` will be set to true in most CI environments, e.g. GitHub Actions, GitLab, Jenkins, etc.
    CI: bool = field(default=os.environ.get("CI") == "true")

    # Users should set this to true to enable replaying events
    AUTOBLOCKS_REPLAYS_ENABLED: bool = field(default=os.environ.get("AUTOBLOCKS_REPLAYS_ENABLED") == "true")

    # The directory where we store the replayed events in local environments
    AUTOBLOCKS_REPLAYS_DIRECTORY: str = field(
        default=os.environ.get("AUTOBLOCKS_REPLAYS_DIRECTORY", "autoblocks-replays")
    )

    # The file where we store the replayed events in CI environments
    AUTOBLOCKS_REPLAYS_FILEPATH: str = field(default=os.environ.get("AUTOBLOCKS_REPLAYS_FILEPATH", "replays.json"))


env = Env()
