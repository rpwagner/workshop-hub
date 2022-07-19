#!/bin/bash

JUPYTERHUB_CRYPT_KEY=$(cat /etc/jupyterhub/crypt.key) \
  GLOBUS_OAUTH_SECRET=$(cat /etc/jupyterhub/globus-oauth-secret.txt) \
  /usr/local/bin/jupyterhub  --config=/etc/jupyterhub/jupyterhub_config.py 1>>/var/log/jupyterhub.log 2>&1 &

