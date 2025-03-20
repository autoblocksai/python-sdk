import os
from typing import Optional

import click
import yaml

from autoblocks._impl.prompts.autogenerate import write_generated_code_for_config
from autoblocks._impl.prompts.cli.models import YamlConfig
from autoblocks._impl.prompts.v2.autogenerate import write_generated_code_for_config as write_v2_generated_code_for_config
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
@click.option(
    "--api-version",
    type=click.Choice(["v1", "v2", "all"]),
    default="v1",
    help="API version to generate prompts for",
)
@click.option(
    "--app-id",
    help="Only generate prompts for this specific app ID (V2 only)",
)
def generate(config_path: Optional[str], api_version: str, app_id: Optional[str]) -> None:
    """Generate code for prompts based on configuration file."""
    # Check V1 API key if needed
    if api_version in ["v1", "all"]:
        if not AutoblocksEnvVar.API_KEY.get():
            msg = (
                f"You must set the {AutoblocksEnvVar.API_KEY} environment variable to your API key in order to "
                f"use this command for V1. You can find your API key at https://app.autoblocks.ai/settings/api-keys."
            )
            if api_version == "v1":
                raise click.ClickException(msg)
            else:
                click.echo(f"Warning: {msg}")
    
    # Check V2 API key if needed
    if api_version in ["v2", "all"]:
        if not AutoblocksEnvVar.V2_API_KEY.get():
            msg = (
                f"You must set the {AutoblocksEnvVar.V2_API_KEY} environment variable to your V2 API key in order to "
                f"use this command for V2."
            )
            if api_version == "v2":
                raise click.ClickException(msg)
            else:
                click.echo(f"Warning: {msg}")

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
    
    # Track if we've processed any section
    processed_any = False
    
    # Handle V1 prompts
    if api_version in ["v1", "all"] and AutoblocksEnvVar.API_KEY.get():
        if config.autogenerate and config.autogenerate.prompts:
            try:
                write_generated_code_for_config(config.autogenerate.prompts)
                processed_any = True
                click.echo(f"Successfully generated V1 prompts at {config.autogenerate.prompts.outfile}")
            except Exception as e:
                click.echo(f"Error generating V1 prompts: {str(e)}")
    
    # Handle V2 prompts
    if api_version in ["v2", "all"] and AutoblocksEnvVar.V2_API_KEY.get():
        v2_configs = config.get_v2_configs()
        
        if not v2_configs:
            if api_version == "v2":
                click.echo("Warning: No V2 prompt configurations found in config file")
        else:
            for section_name, app_config in v2_configs.items():
                # Skip if app_id is specified and doesn't match
                if app_id and app_config.app_id != app_id:
                    continue
                
                try:
                    write_v2_generated_code_for_config(app_config)
                    processed_any = True
                    click.echo(f"Successfully generated V2 prompts at {app_config.outfile} for app {app_config.app_id}")
                except Exception as e:
                    click.echo(f"Error generating V2 prompts for app {app_config.app_id}: {str(e)}")
    
    if not processed_any:
        if app_id:
            click.echo(f"Warning: No matching configurations found for app_id: {app_id}")
        else:
            click.echo("Warning: No prompt configurations were processed")


def main() -> None:
    prompts()
