FROM ghcr.io/rpwagner/mlflow-proxy:latest

USER root

# Startup hook: starts Hermes before JupyterLab starts.
#COPY scripts/20-start-hermes-gateway.sh /usr/local/bin/before-notebook.d/20-start-hermes-gateway.sh
#RUN chmod +x /usr/local/bin/before-notebook.d/20-start-hermes-gateway.sh

# Jupyter Server / jupyter-server-proxy configuration.
COPY jupyter_server_config.py /home/jovyan/.jupyter/jupyter_server_config.py

USER $NB_UID