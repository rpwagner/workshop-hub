#!/bin/bash

eval "$(/usr/local/miniconda/bin/conda shell.bash hook)"

JUPYTERHUB_CRYPT_KEY=$(cat /etc/jupyterhub/crypt.key) \
  GLOBUS_OAUTH_SECRET=$(cat /etc/jupyterhub/globus-oauth-secret.txt) \
    jupyterhub  --config=/etc/jupyterhub/jupyterhub_config.py 
