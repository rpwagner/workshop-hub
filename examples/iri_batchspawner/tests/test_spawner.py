import asyncio
import base64
import json
import pickle
import runpy
import traceback
from pathlib import Path

import pytest
from batchspawner.batchspawner import JobStatus
from jupyterhub import orm
from jupyterhub.objects import Hub
from jupyterhub.user import User
from oauthenticator.globus import GlobusOAuthenticator
from traitlets.config import Config

from iri_batchspawner import IRIBatchSpawner

from .conftest import SCOPE, TOKEN

pytestmark = pytest.mark.asyncio


async def test_start_uses_real_client_and_upstream_start(spawner, iri, caplog):
    iri.states = ["queued", "held", "active"]
    spawner.job_parameters = {
        "resources": {"node_count": 2, "exclusive_node_use": False},
        "attributes": {
            "queue_name": "any-queue",
            "account": "any-project",
            "duration": 900,
        },
        "directory": "/work/any-user",
        "pre_launch": "module load notebooks",
    }
    spawner.args = ["--ServerApp.default_url=/lab", "--ServerApp.log_level=WARNING"]
    spawner.environment = {"GLOBUS_DATA": "never-send-auth-state", "CUSTOM": "value"}
    assert await asyncio.wait_for(spawner.start(), 2) == ("worker.example.org", 54321)
    assert isinstance(spawner, IRIBatchSpawner)
    method, url, headers, body, kwargs = iri.calls[0]
    assert (method, url) == (
        "POST",
        "https://iri.example.org/api/v1/compute/job/test-resource",
    )
    assert headers["Authorization"] == f"Bearer {TOKEN}"
    assert kwargs["_request_timeout"] == 30
    assert body["executable"] == "iri-batchspawner-singleuser"
    assert body["arguments"] == [*spawner.cmd, *spawner.args]
    assert body["resources"]["node_count"] == 2
    assert body["attributes"]["queue_name"] == "any-queue"
    assert body["attributes"]["account"] == "any-project"
    assert body["attributes"]["duration"] == 900
    assert body["directory"] == "/work/any-user"
    assert body["pre_launch"] == "module load notebooks"
    assert body["environment"]["JUPYTERHUB_API_TOKEN"] == spawner.api_token
    assert body["environment"]["CUSTOM"] == "value"
    assert "GLOBUS_DATA" not in body["environment"]
    assert TOKEN not in json.dumps(body)
    assert body["inherit_environment"] is False
    assert spawner.orm_spawner.state["job_id"] == "123.server"
    assert TOKEN not in json.dumps(spawner.get_state())
    assert TOKEN not in caplog.text
    assert await spawner.poll() is None
    assert "historical=true" in iri.calls[-1][1]
    assert "include_spec=false" in iri.calls[-1][1]


@pytest.mark.parametrize(
    "state,expected,exit_code",
    [
        ("new", None, None),
        ("queued", None, None),
        ("held", None, None),
        ("active", None, None),
        ("completed", 0, None),
        ("canceled", 0, None),
        ("failed", 1, None),
        ("failed", 42, 42),
    ],
)
async def test_poll_mapping(spawner, iri, state, expected, exit_code):
    await spawner.submit_batch_script()
    iri.states = [state]
    iri.exit_code = exit_code
    assert await spawner.poll() == expected
    assert bool(spawner.job_id) is (expected is None)


async def test_missing_job_and_uninitialized_poll(spawner, iri):
    assert await spawner.poll() == 0
    await spawner.submit_batch_script()
    iri.http_status = 404
    assert await spawner.poll() == 1
    assert spawner.get_state() == {}


async def test_stop_confirms_cancellation_of_queued_job(spawner, iri):
    await spawner.submit_batch_script()
    iri.states = ["queued", "held", "canceled"]
    await spawner.stop()
    method, url, headers, _, _ = iri.calls[1]
    assert (method, url) == (
        "DELETE",
        "https://iri.example.org/api/v1/compute/cancel/test-resource/123.server",
    )
    assert headers["Authorization"] == f"Bearer {TOKEN}"
    assert spawner.get_state() == {}


async def test_stop_now_and_timeout_preserve_identity(spawner, iri):
    await spawner.submit_batch_script()
    await spawner.stop(now=True)
    assert spawner.job_id == "123.server"
    spawner.stop_timeout = 0.1
    iri.states = ["active"]
    with pytest.raises(RuntimeError, match="not yet confirmed"):
        await spawner.stop()
    assert spawner.job_id == "123.server"


async def test_recovery_uses_saved_target_and_current_auth_state(spawner, iri):
    await spawner.start()
    iri.extra_status = {"message": TOKEN, "meta_data": {"credential": TOKEN}}
    assert await spawner.query_job_status() == JobStatus.RUNNING
    state = json.loads(json.dumps(spawner.get_state()))
    assert TOKEN not in json.dumps(state)
    spawner.clear_state()
    spawner.api_url = "https://different.example.org"
    spawner.resource_id = "different-resource"
    spawner.resource_server = "different-auth-service"
    spawner.load_state(state)
    assert (spawner.ip, spawner.port) == ("worker.example.org", 54321)

    async def updated_auth_state():
        return {
            "tokens": {"synthetic-iri": {"access_token": "fresh-token", "scope": SCOPE}}
        }

    spawner.user.get_auth_state = updated_auth_state
    assert await spawner.poll() is None
    assert iri.calls[-1][1].startswith("https://iri.example.org/api/v1/")
    assert iri.calls[-1][2]["Authorization"] == "Bearer fresh-token"
    iri.states = ["canceled"]
    await spawner.stop()
    assert "different-resource" not in iri.calls[-2][1]


@pytest.mark.parametrize(
    "info",
    [
        None,
        {},
        {"access_token": TOKEN, "scope": "wrong"},
        {"access_token": "", "scope": SCOPE},
    ],
)
async def test_missing_or_unscoped_token_fails_without_exposure(
    spawner, iri, info, caplog
):
    spawner.token_provider = lambda _: info
    with pytest.raises(RuntimeError, match="scoped IRI") as error:
        await spawner.submit_batch_script()
    assert iri.calls == []
    assert TOKEN not in str(error.value) + caplog.text
    assert spawner.get_state() == {}


async def test_async_token_provider_is_used_for_each_operation(spawner, iri):
    calls = []

    async def token_provider(s):
        calls.append(s)
        return {"access_token": TOKEN, "scope": SCOPE}

    spawner.token_provider = token_provider
    await spawner.submit_batch_script()
    await spawner.poll()
    await spawner.stop(now=True)
    assert calls == [spawner] * 3
    assert TOKEN not in json.dumps(spawner.get_state())


@pytest.mark.parametrize("http_status", [401, 403, 429, 500, 503])
async def test_api_error_is_redacted_and_retains_job(spawner, iri, http_status, caplog):
    await spawner.submit_batch_script()
    iri.http_status = http_status
    with pytest.raises(RuntimeError, match=f"HTTP {http_status}") as error:
        await spawner.poll()
    assert TOKEN not in str(error.value) + caplog.text
    assert TOKEN not in "".join(traceback.format_exception(error.value))
    assert spawner.job_id == "123.server"


async def test_restart_with_real_hub_database_and_new_spawner(iri):
    factory = orm.new_session_factory()
    db = factory()
    db.add(orm.User(name="synthetic-user"))
    db.commit()
    user = User(db.query(orm.User).one(), {})
    options = dict(
        spawner_class=IRIBatchSpawner,
        hub=Hub(),
        api_url="https://iri.example.org",
        resource_id="test-resource",
        resource_server="synthetic-iri",
        required_scopes=[SCOPE],
        token_provider=lambda _: {"access_token": TOKEN, "scope": SCOPE},
        startup_poll_interval=0.001,
    )
    try:
        original = user._new_spawner("", **options)
        original.api_token = "synthetic-hub-token"
        iri.spawner = original
        assert await original.start() == ("worker.example.org", 54321)
        # Identity was committed by submission before ready-state saving.
        with factory() as reader:
            saved = reader.query(orm.Spawner).one().state
            assert saved["job_id"] == "123.server"
            assert TOKEN not in json.dumps(saved)
        # Match the normal Hub's post-start save of spawner state.
        original.orm_spawner.state = original.get_state()
        db.commit()
        with factory() as restarted_db:
            restarted_user = User(restarted_db.query(orm.User).one(), {})
            recovered = restarted_user._new_spawner("", **options)
            assert recovered is not original
            assert recovered.job_id == "123.server"
            assert (recovered.ip, recovered.port) == ("worker.example.org", 54321)
            assert await recovered.poll() is None
            iri.states = ["canceled"]
            await recovered.stop()
    finally:
        db.close()


@pytest.mark.parametrize("parameters", [{"environment": {}}, {"queue": "typo"}])
async def test_invalid_job_configuration_fails_before_submission(
    spawner, iri, parameters
):
    spawner.job_parameters = parameters
    with pytest.raises(ValueError):
        await spawner.submit_batch_script()
    assert not iri.calls


async def test_late_endpoint_callback_after_active_state(spawner, iri):
    iri.report_endpoint = False
    task = asyncio.create_task(spawner.start())
    while not spawner.state_isrunning():
        await asyncio.sleep(0.001)
    spawner.ip = "late-worker.example.org"
    spawner.port = 12345
    assert await asyncio.wait_for(task, 2) == ("late-worker.example.org", 12345)


async def test_missing_endpoint_times_out_with_job_retained_for_cleanup(spawner, iri):
    iri.report_endpoint = False
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(spawner.start(), 0.1)
    assert spawner.job_id == "123.server"
    iri.states = ["canceled"]
    await spawner.stop()


async def test_submission_cancellation_records_id_for_hub_cleanup(
    spawner, iri, monkeypatch
):
    original_call = spawner._call
    entered = asyncio.Event()
    release = asyncio.Event()

    async def delayed(operation, **kwargs):
        if operation == "launch_job":
            entered.set()
            await release.wait()
        return await original_call(operation, **kwargs)

    monkeypatch.setattr(spawner, "_call", delayed)
    start = asyncio.create_task(spawner.start())
    await entered.wait()
    start.cancel()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await start
    assert spawner.job_id == spawner.orm_spawner.state["job_id"] == "123.server"
    iri.states = ["canceled"]
    await spawner.stop()
    assert iri.calls[-2][0] == "DELETE"


async def test_globus_authenticator_real_auth_state_and_environment(spawner, iri):
    authenticator = GlobusOAuthenticator()
    token_info = {
        "access_token": "auth-access",
        "scope": "openid profile",
        "resource_server": "auth.globus.org",
        "other_tokens": [
            {
                "resource_server": "synthetic-iri",
                "access_token": TOKEN,
                "refresh_token": "never-forward-refresh",
                "scope": SCOPE,
            }
        ],
    }
    state = authenticator.build_auth_state_dict(
        token_info, {"preferred_username": "someone"}
    )

    async def auth_state():
        return state

    spawner.user.get_auth_state = auth_state
    await authenticator.pre_spawn_start(spawner.user, spawner)
    # Verify this really exercised upstream's credential-forwarding behavior.
    raw = pickle.loads(base64.b64decode(spawner.environment["GLOBUS_DATA"]))
    assert raw["tokens"]["synthetic-iri"]["access_token"] == TOKEN
    await spawner.submit_batch_script()
    assert TOKEN not in json.dumps(iri.calls[0][3])
    assert "never-forward-refresh" not in json.dumps(iri.calls[0][3])


@pytest.mark.parametrize(
    "url",
    [
        "http://iri.example.org",
        "https://user:secret@iri.example.org",
        "https://iri.example.org/api/v1",
        "https://iri.example.org?x=1",
    ],
)
async def test_invalid_origin_is_rejected(spawner, iri, url):
    spawner.api_url = url
    with pytest.raises(ValueError, match="HTTPS service origin"):
        await spawner.submit_batch_script()
    assert iri.calls == []


async def test_example_configuration_loads(monkeypatch):
    names = [
        "GLOBUS_CLIENT_ID",
        "GLOBUS_CLIENT_SECRET",
        "GLOBUS_CALLBACK_URL",
        "HUB_IDENTITY_PROVIDER",
        "HUB_ALLOWED_GLOBUS_GROUPS",
        "IRI_RESOURCE_ID",
        "IRI_JOB_DIRECTORY",
        "IRI_STDOUT_PATH",
        "IRI_STDERR_PATH",
        "IRI_QUEUE",
        "IRI_ACCOUNT",
        "IRI_SINGLEUSER_WRAPPER",
        "IRI_SINGLEUSER_COMMAND",
        "HUB_BIND_URL",
        "HUB_CONNECT_URL",
    ]
    for name in names:
        monkeypatch.setenv(name, "synthetic-value")
    monkeypatch.setenv("IRI_NODE_COUNT", "1")
    monkeypatch.setenv("IRI_DURATION_SECONDS", "300")
    config = Config()
    runpy.run_path(
        str(Path(__file__).parents[1] / "jupyterhub_config.py"),
        init_globals={"get_config": lambda: config},
    )
    authenticator = GlobusOAuthenticator(config=config)
    instance = IRIBatchSpawner(config=config)
    assert instance.resource_id == "synthetic-value"
    assert instance.resource_server not in authenticator.exclude_tokens
    assert set(instance.required_scopes).issubset(authenticator.scope)
    assert authenticator.enable_auth_state
