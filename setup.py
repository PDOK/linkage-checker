from configparser import ConfigParser

from setuptools import setup, find_packages

version = "0.3.dev0"

long_description = "\n\n".join([open("README.md").read(), open("CHANGES.md").read()])


def parse_pipfile(development=False):
    """Reads package requirements from Pipfile."""
    cfg = ConfigParser()
    cfg.read('Pipfile')
    dev_packages = [p.strip('"') for p in cfg['dev-packages']]
    relevant_packages = [
        p.strip('"') for p in cfg['packages'] if "linkage-checker" not in p
    ]
    if development:
        return dev_packages
    else:
        return relevant_packages


setup(
    name="linkage-checker",
    version=version,
    description="Python wrapper that runs and aggregates the INSPIRE linkage checker",
    long_description=long_description,
    # Get strings from http://www.python.org/pypi?%3Aaction=list_classifiers
    classifiers=["Programming Language :: Python :: 3"],
    keywords=["linkage-checker"],
    author="pdok.nl",
    url="https://github.com/PDOK/linkage-checker",
    packages=find_packages(exclude=['tests']),
    include_package_data=True,
    zip_safe=False,
    install_requires=parse_pipfile(),
    tests_require=parse_pipfile(True),
    entry_points={
        "console_scripts": ["linkage-checker = linkage_checker.cli:linkage_checker_command"]
    },
)
