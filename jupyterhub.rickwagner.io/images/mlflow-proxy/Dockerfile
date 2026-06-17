FROM quay.io/jupyter/base-notebook:hub-5.5.0

USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
    emacs-nox \
    git \
    curl \
    ca-certificates \
    ripgrep \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN python3 -m pip install --root-user-action=ignore -r /tmp/requirements.txt

USER $NB_UID