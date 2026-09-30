from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import requests

from iri_batchspawner import singleuser


@pytest.mark.parametrize("override", [None, "routable.example.org"])
def test_host_callback_precedes_upstream_port_launcher(monkeypatch, override):
    auth = SimpleNamespace(
        api_url="https://hub.example.org/hub/api",
        api_token="hub-token",
        certfile="cert.pem",
        keyfile="key.pem",
        client_ca="ca.pem",
    )
    monkeypatch.setattr(singleuser, "HubAuth", lambda: auth)
    monkeypatch.setattr(singleuser.socket, "getfqdn", lambda: "worker.example.org")
    monkeypatch.delenv("IRI_JUPYTER_HOST", raising=False)
    if override:
        monkeypatch.setenv("IRI_JUPYTER_HOST", override)
    post = Mock(return_value=Mock())
    monkeypatch.setattr(singleuser.requests, "post", post)

    def launch():
        post.return_value.raise_for_status.assert_called_once()

    monkeypatch.setattr(singleuser, "batchspawner_main", launch)
    singleuser.main()
    post.assert_called_once_with(
        "https://hub.example.org/hub/api/batchspawner",
        headers={"Authorization": "token hub-token"},
        json={"ip": override or "worker.example.org"},
        timeout=30,
        cert=("cert.pem", "key.pem"),
        verify="ca.pem",
    )


def test_failed_callback_does_not_launch_or_expose_response(monkeypatch, caplog):
    auth = SimpleNamespace(
        api_url="https://hub.example.org/hub/api",
        api_token="secret-token",
        certfile=None,
        keyfile=None,
        client_ca=None,
    )
    monkeypatch.setattr(singleuser, "HubAuth", lambda: auth)
    monkeypatch.setattr(
        singleuser.requests,
        "post",
        Mock(side_effect=requests.HTTPError("secret-token")),
    )
    launch = Mock()
    monkeypatch.setattr(singleuser, "batchspawner_main", launch)
    with pytest.raises(RuntimeError, match="report execution host") as error:
        singleuser.main()
    launch.assert_not_called()
    assert "secret-token" not in str(error.value) + caplog.text
