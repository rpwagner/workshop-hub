"""Report the execution host, then use BatchSpawner's single-user launcher."""

import os
import socket

import requests
from batchspawner.singleuser import main as batchspawner_main
from jupyterhub.services.auth import HubAuth
from jupyterhub.utils import url_path_join


def main():
    auth = HubAuth()
    host = os.environ.get("IRI_JUPYTER_HOST") or socket.getfqdn()
    kwargs = {"timeout": 30}
    if auth.certfile and auth.keyfile:
        kwargs["cert"] = (auth.certfile, auth.keyfile)
    if auth.client_ca:
        kwargs["verify"] = auth.client_ca
    try:
        response = requests.post(
            url_path_join(auth.api_url, "batchspawner"),
            headers={"Authorization": f"token {auth.api_token}"},
            json={"ip": host},
            **kwargs,
        )
        response.raise_for_status()
    except requests.RequestException:
        raise RuntimeError("Unable to report execution host to the Hub") from None
    # Upstream owns port allocation, its authenticated port callback, service
    # URL binding and launching the requested jupyterhub-singleuser command.
    batchspawner_main()
