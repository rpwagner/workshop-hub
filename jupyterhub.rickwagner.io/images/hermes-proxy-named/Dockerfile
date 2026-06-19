FROM ghcr.io/rpwagner/mlflow-proxy:latest

USER root

COPY start-hermes-gateway /usr/local/bin/start-hermes-gateway
RUN chmod +x /usr/local/bin/start-hermes-gateway

COPY jupyter_server_config.py /etc/jupyter/jupyter_server_config.py

USER $NB_UID
