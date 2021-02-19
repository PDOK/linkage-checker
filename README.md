# linkage-checker
Python wrapper that runs the [INSPIRE linkage checker](https://inspire-geoportal.ec.europa.eu/linkagechecker.html) and aggregates the results. _This is a proof of concept. It is tested with the INSPIRE linkage checker version: [1.4.0](https://inspire-geoportal.ec.europa.eu/release-notes.html)_

# Usage
At this moment, the linkage-checker uses a [selenium docker image](https://github.com/SeleniumHQ/docker-selenium) for using and running the INSPIRE linkage checker.

First, start a selenium docker container with:
```bash
docker run --rm -p 4444:4444 -v /dev/shm:/dev/shm selenium/standalone-firefox:3.141.59-20201010
```
Now the linkage-checker can be used and started with a command.

_Unfortunately there is no INSPIRE linkage checker API available at the moment. Therefore, it is being investigated whether this way (using selenium) can be replaced by running the INSPIRE linkage checker only via http requests (which is faster, more stable and more efficient - in terms of execution speed and memory usage), so that the use of a selenium container is no longer necessary._

## Commands

```bash
Usage: linkage-checker [OPTIONS]

Options:
  --output-path PATH              Path to a json file where the linkage
                                  checker results will be stored.

  --remote_selenium_url URL       Connection URL of the selenium (remote)
                                  webdriver.
  
  --enable-caching                Cache the NGR records in a local
                                  json file (useful for debugging
                                  purposes).

  --browser-screenshots           Take browser screenshots for
                                  debugging purposes.

  -d, --debug-mode                Enables debug mode which will run
                                  tests for the first three NGR
                                  records.
                                  
  -v, --verbosity LVL             Either CRITICAL, ERROR, WARNING,
                                  INFO or DEBUG.

  --help                          Show this message and exit.
```

Examples:

Normal run:
```bash
pipenv run linkage-checker --output-path /example/results.json
```

With some debugging functionalities enabled:
```bash
pipenv run linkage-checker --enable-caching --browser-screenshots -v DEBUG --debug-mode
```

## Development installation of this project itself

We're installed with [pipenv](https://docs.pipenv.org/), a handy wrapper
around pip and virtualenv. Install that first with `pip3 install pipenv`. Then run:

```bash
PIPENV_VENV_IN_PROJECT=1 pipenv install --python 3.8 --dev
```

In case you do not have python 3.8 on your machine, install python using 
[pyenv](https://github.com/pyenv/pyenv) and try the previous command again.
See install pyenv below for instructions. 

There will be a script you can run like this::

```bash
pipenv run linkage-checker
```

It runs the `main()` function in `linkage-checker/scripts.py`,
adjust that if necessary. The script is configured in `setup.py` (see
`entry_points`).

In order to get nicely formatted python files without having to spend manual
work on it, run the following command periodically:

```bash
pipenv run black linkage_checker
```

Run the tests regularly. This also checks with pyflakes, black and it reports
coverage. Pure luxury:

```bash
pipenv run pytest
```

If you need a new dependency (like `requests`), add it in `setup.py` in
`install_requires`. Afterwards, run install again to actually install your
dependency:

```bash
pipenv install --dev
```

## Releasing 
Pipenv installs zest.releaser which allows you to release the package to a git(hub) repo. It has a 
`fullrelease` command that asks you a few questions, which you all respond to with `<enter>`:

```bash
pipenv run fullrelease
```
# Install pyenv
We can install pyenv by running the following commands: 

```bash
sudo apt-get install -y make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev
curl -L https://github.com/pyenv/pyenv-installer/raw/master/bin/pyenv-installer | bash
```

Also make sure to put pyenv in your `.bashrc` or `.zshrc` as instructed by the previous commands. 
