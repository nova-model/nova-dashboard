FROM --platform=amd64 regproxy.ornl.gov/hub_proxy/ubuntu:noble AS source
ARG DEBIAN_FRONTEND=noninteractive

# make sure image can run as non-root user
ENV PNPM_HOME=/pnpm
ENV POETRY_CACHE_DIR=/poetry/.cache
ENV POETRY_CONFIG_DIR=/poetry/.config
ENV POETRY_HOME=/poetry

RUN apt update && apt upgrade -y && apt install -y \
    curl \
    gettext-base \
    software-properties-common \
    nginx
RUN add-apt-repository ppa:deadsnakes/ppa -y
RUN apt update && apt install -y \
    python3.10

# Install Poetry
RUN curl -fsSL https://install.python-poetry.org | python3.10 -
ENV PATH="$PATH:$POETRY_HOME/bin"

# Install Node.js LTS & pnpm
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
RUN apt install -y nodejs
ENV SHELL=bash
RUN curl -fsSL https://get.pnpm.io/install.sh | sh -
ENV PATH="$PATH:$PNPM_HOME"

# Setup Django
ADD ./ /opt/run/django
WORKDIR /opt/run/django
RUN poetry install

# Setup Vue.js
ADD src/vue /opt/run/vue
WORKDIR /opt/run/vue
RUN pnpm install

WORKDIR /opt/run/django
RUN chmod og+rwX /pnpm
RUN chmod og+rwX /poetry
RUN chmod og+rwX /opt/run/django


FROM source AS run

# Install dependencies only used in production builds
WORKDIR /opt/run/django
RUN poetry run pip install gunicorn uvicorn-worker

# Create static client build
WORKDIR /opt/run/vue
RUN cp /opt/run/django/pyproject.toml /opt/pyproject.toml
RUN pnpm build

ADD dockerfiles/nginx.conf.template /etc/nginx/nginx.conf.template
ADD scripts/entrypoint.sh /opt/run/entrypoint.sh
ADD manage.py /opt/run/django/manage.py

RUN mkdir -p /tmp
RUN mkdir -p /run/nginx

WORKDIR /opt/run/django
# Squash useless warning about missing .env file
RUN touch .env
ENTRYPOINT ["bash", "/opt/run/entrypoint.sh"]
