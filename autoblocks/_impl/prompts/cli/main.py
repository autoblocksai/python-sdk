import os
from typing import Optional

import click
import yaml

from autoblocks._impl.prompts.autogenerate import write_generated_code_for_config
from autoblocks._impl.prompts.cli.models import YamlConfig
from autoblocks._impl.util import AutoblocksEnvVar


def read_config(config_path: str) -> YamlConfig:
    """Reads YAML configuration from the specified path."""
    with open(config_path, "r") as file:
        data = yaml.safe_load(file)
    return YamlConfig.model_validate(data)


@click.group()
def prompts() -> None:
    """Handle prompts-related commands."""
    pass


@prompts.command()
@click.option(
    "--config-path",
    envvar="AUTOBLOCKS_CONFIG_PATH",
    type=click.Path(exists=True),
    help="Path to your Autoblocks config file",
)
def generate(config_path: Optional[str]) -> None:
    if not AutoblocksEnvVar.API_KEY.get():
        msg = (
            f"You must set the {AutoblocksEnvVar.API_KEY} environment variable to your API key in order to "
            f"use this command. You can find your API key at https://app.autoblocks.ai/settings/api-keys."
        )
        raise click.ClickException(msg)

    default_config_paths = (
        ".autoblocks.yaml",
        ".autoblocks.yml",
    )
    if not config_path:
        for path in default_config_paths:
            if os.path.exists(path):
                config_path = path
                break
        else:
            msg = (
                "No configuration file found. Either specify a path to your Autoblocks YAML configuration file with "
                "--config-path or create one of the following files:\n"
            )
            for path in default_config_paths:
                msg += f"- {path}" + "\n"
            raise click.ClickException(msg.strip())

    config = read_config(config_path)

    write_generated_code_for_config(config.autogenerate.prompts)
    click.echo(f"Successfully generated prompts at {config.autogenerate.prompts.outfile}")


def main() -> None:
    prompts()
