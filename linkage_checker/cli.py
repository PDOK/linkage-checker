# -*- coding: utf-8 -*-
"""Main CLI entry for the linkage-checker tool."""
import logging
import sys

import click
import click_log

# Setup logging before package imports.
logger = logging.getLogger(__name__)
click_log.basic_config(logger)

from linkage_checker.core import main
from linkage_checker.error import AppError


def set_log_level():
    loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]
    for logger_ in loggers:
        logger_.setLevel(logger.level)
    logging.info("Set loglevels to %s.", logging.getLevelName(logger.level))


@click.group()
def cli():
    pass


@cli.command(name="linkage-checker")
@click.option(
    "--output-path",
    required=False,
    default=None,
    help="Path to a json file where the linkage checker results will be stored.",
    type=click.types.Path(
        exists=False,
        file_okay=True,
        dir_okay=True,
        readable=True,
        writable=True,
        allow_dash=False,
    ),
)
@click.option(
    '--enable-caching',
    is_flag=True,
    default=False,
    help="Cache the NGR records in a local json file (useful for debugging purposes)."
)
@click.option(
    '--browser-screenshots',
    is_flag=True,
    default=False,
    help="Take browser screenshots for debugging purposes."
)
@click_log.simple_verbosity_option(logger)
def linkage_checker_command(output_path, enable_caching, browser_screenshots):
    set_log_level()

    try:
        main(output_path, enable_caching, browser_screenshots)
    except AppError:
        logger.exception("linkage-checker failed:")
        sys.exit(1)


if __name__ == "__main__":
    cli()
