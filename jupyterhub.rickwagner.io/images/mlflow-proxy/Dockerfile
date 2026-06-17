FROM quay.io/jupyter/base-notebook:hub-5.5.0

USER root

ENV DEBIAN_FRONTEND=noninteractive
ENV HERMES_HOME=/home/jovyan/work/.hermes
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright
ENV AGENT_BROWSER_ARGS=--no-sandbox,--disable-dev-shm-usage

RUN apt-get update && apt-get install -y --no-install-recommends \
    emacs-nox \
    git \
    curl \
    ca-certificates \
    ripgrep \
    ffmpeg \
    xz-utils \
    openssh-client \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN python3 -m pip install --root-user-action=ignore -r /tmp/requirements.txt

RUN npm install -g agent-browser playwright \
    && npx playwright install --with-deps chromium --only-shell \
    && npm cache clean --force \
    && chmod -R a+rX /opt/playwright
    
USER $NB_UID
