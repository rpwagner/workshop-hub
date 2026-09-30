"""Synthetic IRI transport; the real generated client remains under test."""

import asyncio
import io
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import pytest_asyncio
from amsc_iri.rest import RESTClientObject
from jupyterhub.objects import Hub
from urllib3 import HTTPResponse

from iri_batchspawner import IRIBatchSpawner

SCOPE = "https://auth.globus.org/scopes/synthetic-iri/compute"
TOKEN = "synthetic-user-access-token"


@pytest.fixture
def spawner():
    async def auth_state():
        return {
            "tokens": {
                "synthetic-iri": {"access_token": TOKEN, "scope": SCOPE},
                "unrelated": {"access_token": "wrong-service", "scope": "other"},
            }
        }

    return IRIBatchSpawner(
        api_url="https://iri.example.org",
        resource_id="test-resource",
        resource_server="synthetic-iri",
        required_scopes=[SCOPE],
        user=SimpleNamespace(
            name="no-local-posix-account", url="/user/test/", get_auth_state=auth_state
        ),
        hub=Hub(),
        orm_spawner=SimpleNamespace(name="", server=None, state={}),
        db=Mock(),
        api_token="synthetic-hub-api-token",
        cmd=["/opt/notebook/bin/jupyterhub-singleuser"],
        startup_poll_interval=0.001,
    )


@pytest_asyncio.fixture
async def iri(monkeypatch, spawner):
    loop = asyncio.get_running_loop()
    fake = SimpleNamespace(
        spawner=spawner,
        calls=[],
        states=["active"],
        http_status=200,
        report_endpoint=True,
        exit_code=None,
        extra_status={},
    )

    def request(client, method, url, headers=None, body=None, **kwargs):
        fake.calls.append((method, url, headers, body, kwargs))
        if fake.http_status != 200:
            return HTTPResponse(
                status=fake.http_status,
                body=json.dumps({"detail": TOKEN}).encode(),
                headers={"Content-Type": "application/json"},
            )
        if method == "DELETE":
            return HTTPResponse(status=204, body=io.BytesIO(b""))
        if method == "POST":
            if fake.report_endpoint:
                # Emulate the two ordered upstream authenticated callbacks.
                loop.call_soon_threadsafe(
                    setattr, fake.spawner, "ip", "worker.example.org"
                )
                loop.call_soon_threadsafe(setattr, fake.spawner, "port", 54321)
            payload = {"id": "123.server"}
        else:
            state = fake.states.pop(0) if len(fake.states) > 1 else fake.states[0]
            payload = {
                "id": "123.server",
                "status": {
                    "state": state,
                    "exit_code": fake.exit_code,
                    **fake.extra_status,
                },
            }
        return HTTPResponse(
            status=200,
            body=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )

    monkeypatch.setattr(RESTClientObject, "request", request)
    return fake
