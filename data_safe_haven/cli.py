"""Command line entrypoint for Data Safe Haven application"""

import pathlib
from typing import Annotated, Optional

import typer

from data_safe_haven import __version__
from data_safe_haven.commands import (
    admin_command_group,
    config_command_group,
    context_command_group,
    deploy_command_group,
    teardown_command_group,
)
from data_safe_haven.exceptions import DataSafeHavenError
from data_safe_haven.utility import LoggingSingleton


def callback(
    output: Annotated[
        Optional[pathlib.Path],  # noqa: UP007
        typer.Option(
            "--output", "-o", resolve_path=True, help="Path to an output log file"
        ),
    ] = None,
    verbosity: Annotated[
        Optional[int],  # noqa: UP007
        typer.Option(
            "--verbosity",
            "-v",
            help="Increase the verbosity of messages: each '-v' will increase by one step.",
            count=True,
            is_eager=True,
        ),
    ] = None,
    version: Annotated[
        Optional[bool],  # noqa: UP007
        typer.Option(
            "--version", "-V", help="Display the version of this application."
        ),
    ] = None,
) -> None:
    """Arguments to the main executable"""
    logger = LoggingSingleton()
    if output:
        logger.set_log_file(output)
    if verbosity:
        logger.set_verbosity(verbosity)
    if version:
        print(f"Data Safe Haven {__version__}")  # noqa: T201
        raise typer.Exit()


def application() -> typer.Typer:
    """Command line entrypoint for Data Safe Haven application"""

    # Create the application
    application = typer.Typer(
        context_settings={"help_option_names": ["-h", "--help"]},
        invoke_without_command=True,
        no_args_is_help=True,
    )

    # Register arguments to the main executable
    application.callback()(callback)

    # Register command groups
    application.add_typer(
        admin_command_group,
        name="admin",
        help="Perform administrative tasks for a Data Safe Haven deployment.",
    )
    application.add_typer(
        config_command_group,
        name="config",
        help="Manage Data Safe Haven configuration.",
    )
    application.add_typer(
        context_command_group, name="context", help="Manage Data Safe Haven contexts."
    )
    application.add_typer(
        deploy_command_group,
        name="deploy",
        help="Deploy a Data Safe Haven component.",
    )
    application.add_typer(
        teardown_command_group,
        name="teardown",
        help="Tear down a Data Safe Haven component.",
    )

    return application


def main() -> None:
    """Run the application and log any exceptions"""
    try:
        application()()
    except DataSafeHavenError as exc:
        logger = LoggingSingleton()
        for line in str(exc).split("\n"):
            logger.error(line)
