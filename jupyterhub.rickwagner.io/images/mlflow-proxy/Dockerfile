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

RUN mkdir -p /usr/local/bin/start-notebook.d \
 && cat > /usr/local/bin/start-notebook.d/20-setup-hermes-home.sh <<'EOF' \
 && chmod +x /usr/local/bin/start-notebook.d/20-setup-hermes-home.sh
#!/usr/bin/env bash
set -euo pipefail

: "${HERMES_HOME:=/home/jovyan/work/.hermes}"

mkdir -p "$HERMES_HOME"
chmod 700 "$HERMES_HOME"

if [ ! -e /home/jovyan/.hermes ]; then
    ln -s "$HERMES_HOME" /home/jovyan/.hermes
fi
EOF
    
USER $NB_UID
