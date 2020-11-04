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


@click.group()
def cli():
    pass


@cli.command(name="linkage-checker")
@click.option('--enable-caching', is_flag=True, default=False)
@click.option('--browser-screenshots', is_flag=True, default=False)
@click_log.simple_verbosity_option(logger)
def linkage_checker_command(enable_caching, browser_screenshots):
    try:
        main(logger, enable_caching, browser_screenshots)
    except AppError:
        logger.exception("linkage-checker failed:")
        sys.exit(1)


if __name__ == "__main__":
    cli()
