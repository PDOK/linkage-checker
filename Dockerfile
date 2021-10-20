FROM python:3.8-slim
# We choose python-slim instead of alpine, a buildspeed vs image size tradeoff.

# In case you need base debian dependencies install them here.
# RUN apt-get update && apt-get -y upgrade && apt-get install -y --no-install-recommends \
# #        TODO list depencies here \
#    && apt-get clean && rm -rf /var/lib/apt/lists/*

ENV DEBIAN_FRONTEND=noninteractive

# Install dev dependencies
RUN apt-get update && apt-get -y upgrade && apt-get install -y --no-install-recommends \
        gcc \
        python3-dev && \
        apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade --no-cache-dir setuptools pip
RUN pip install --no-cache-dir pipenv

# Copy source
WORKDIR /code
COPY . /code

# Install packages
RUN PIPENV_VENV_IN_PROJECT=1 pipenv --three
RUN pipenv lock
RUN pipenv sync

WORKDIR /code

# Make sure we use the virtualenv:
ENV PATH="/code/.venv/bin:$PATH"

# Metadata params
ARG BUILD_DATE
ARG VERSION
ARG GIT_COMMIT_HASH

# Metadata
LABEL org.opencontainers.image.authors="pdok.nl" \
      org.opencontainers.image.created=$BUILD_DATE \
      org.opencontainers.image.title="linkage-checker" \
      org.opencontainers.image.description="Python wrapper that runs and aggregates the INSPIRE linkage checker" \
      org.opencontainers.image.url="https://github.com/PDOK/linkage-checker" \
      org.opencontainers.image.vendor="PDOK" \
      org.opencontainers.image.source="https://github.com/PDOK/linkage-checker" \
      org.opencontainers.image.revision=$GIT_COMMIT_HASH \
      org.opencontainers.image.version=$VERSION

ENTRYPOINT [ "linkage-checker" ]