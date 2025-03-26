import os
from typing import Optional

import click
import yaml

from autoblocks._impl.prompts.autogenerate import write_generated_code_for_config
from autoblocks._impl.prompts.cli.models import YamlConfig
from autoblocks._impl.prompts.v2.discovery import generate_all_prompt_modules
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
    """Generate code for prompts based on configuration file."""
    if not AutoblocksEnvVar.API_KEY.get():
        msg = (
            f"You must set the {AutoblocksEnvVar.API_KEY} environment variable to your API key in order to "
            f"use this command for V1. You can find your API key at https://app.autoblocks.ai/settings/api-keys."
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

    processed_any = False

    if AutoblocksEnvVar.API_KEY.get():
        if config.autogenerate and config.autogenerate.prompts:
            try:
                write_generated_code_for_config(config.autogenerate.prompts)
                processed_any = True
                click.echo(f"Successfully generated V1 prompts at {config.autogenerate.prompts.outfile}")
            except Exception as e:
                click.echo(f"Error generating V1 prompts: {str(e)}")

    if not processed_any:
        click.echo("Warning: No prompt configurations were processed")


@prompts.command()
@click.option(
    "--output-dir",
    required=True,
    help="Output directory for generated files (e.g., 'autoblocks/prompts/v2')",
)
def generate_v2(api_key: Optional[str] = None, output_dir: Optional[str] = None) -> None:
    """Generate V2 prompt modules from the API."""

    # Check for V2 API key
    api_key = AutoblocksEnvVar.V2_API_KEY.get()

    if not api_key:
        raise click.ClickException(
            f"You must either pass in the API key via '--api-key' or "
            f"set the {AutoblocksEnvVar.V2_API_KEY} environment variable."
        )

    try:
        generate_all_prompt_modules(api_key, output_dir)
        click.echo(f"Successfully generated V2 prompt modules in {output_dir}")
    except Exception as e:
        raise click.ClickException(f"Error generating V2 prompts: {str(e)}")


def main() -> None:
    prompts()
