"""Use the IRI v1 compute API as a BatchSpawner scheduler backend."""

import asyncio
import inspect
from copy import deepcopy
from urllib.parse import urlsplit

from amsc_iri import ApiClient, ComputeApi, Configuration, JobSpec
from amsc_iri.exceptions import ApiException
from batchspawner import BatchSpawnerBase
from batchspawner.batchspawner import JobStatus
from traitlets import Callable, Dict, Float, List, Unicode


class IRIBatchSpawner(BatchSpawnerBase):
    """Override scheduler operations, retaining BatchSpawner's start/callback flow.

    ``token_provider(spawner)`` may return (or await) a token-info dict with
    ``access_token`` and a space-delimited ``scope``. Without it, each operation
    reads ``user.get_auth_state()['tokens'][resource_server]``. Refresh and
    reauthentication remain the authenticator's responsibility.
    """

    api_url = Unicode(help="IRI service origin, without /api/v1").tag(config=True)
    resource_id = Unicode(help="IRI compute resource identifier").tag(config=True)
    resource_server = Unicode(help="Globus Auth resource server identifier").tag(
        config=True
    )
    required_scopes = List(Unicode(), help="IRI scopes required on the user token").tag(
        config=True
    )
    token_provider = Callable(None, allow_none=True).tag(config=True)
    job_parameters = Dict(
        help="IRI JobSpec fields, e.g. resources, attributes, directory, pre_launch. "
        "Executable, arguments and environment are supplied by the spawner."
    ).tag(config=True)
    request_timeout = Float(30, min=0.1).tag(config=True)
    stop_timeout = Float(30, min=0.1).tag(config=True)
    batchspawner_singleuser_cmd = Unicode("iri-batchspawner-singleuser").tag(
        config=True
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._iri_context = {}
        self._exit_code = None

    def _new_context(self):
        url = urlsplit(self.api_url)
        if (
            url.scheme != "https"
            or not url.hostname
            or url.username
            or url.password
            or url.path not in ("", "/")
            or url.query
            or url.fragment
        ):
            raise ValueError("api_url must be an HTTPS service origin")
        if not self.resource_id or not self.resource_server or not self.required_scopes:
            raise ValueError(
                "Configure resource_id, resource_server and required_scopes"
            )
        return {
            "api_url": self.api_url.rstrip("/"),
            "resource_id": self.resource_id,
            "resource_server": self.resource_server,
            "required_scopes": list(self.required_scopes),
        }

    async def _token(self):
        # No cached token/client on the spawner: use current Hub auth state even
        # when poll/stop is called after a Hub restart, without a pre-spawn hook.
        try:
            if self.token_provider is not None:
                info = self.token_provider(self)
                if inspect.isawaitable(info):
                    info = await info
            else:
                state = await self.user.get_auth_state()
                info = state["tokens"][self._iri_context["resource_server"]]
            token = info["access_token"]
            scopes = set(info["scope"].split())
            if not isinstance(token, str) or not token:
                raise ValueError
            if not set(self._iri_context["required_scopes"]).issubset(scopes):
                raise ValueError
        except Exception:
            raise RuntimeError(
                "A scoped IRI user access token is required; reauthenticate through the Hub"
            ) from None
        return token

    async def _call(self, operation, **kwargs):
        token = await self._token()
        origin = self._iri_context["api_url"]
        resource = self._iri_context["resource_id"]
        timeout = self.request_timeout

        def call():
            # The maintained client owns paths, encoding, validation and bearer
            # authentication. Disable HTTP debug output and automatic retries.
            config = Configuration(
                host=origin, access_token=token, debug=False, retries=0
            )
            with ApiClient(config) as client:
                return getattr(ComputeApi(client), operation)(
                    resource_id=resource, _request_timeout=timeout, **kwargs
                )

        try:
            return await asyncio.to_thread(call)
        except ApiException as error:
            # API response bodies may contain the JobSpec/environment. Never
            # propagate or log those bodies, headers, or the original exception.
            if error.status == 404 and operation != "launch_job":
                return None
            raise RuntimeError(
                f"IRI {operation} failed (HTTP {error.status})"
            ) from None
        except Exception:
            raise RuntimeError(f"IRI {operation} failed") from None

    def get_env(self):
        env = super().get_env()
        # GlobusOAuthenticator.pre_spawn_start injects a pickled auth state,
        # including token_response. No Globus credentials go to the IRI job.
        env.pop("GLOBUS_DATA", None)
        env.pop("GLOBUS_LOCAL_ENDPOINT", None)
        return env

    async def submit_batch_script(self):
        if self.job_id:
            raise RuntimeError("An IRI job is already tracked; stop it before spawning")
        self._iri_context = self._new_context()
        parameters = deepcopy(self.job_parameters)
        if {"executable", "arguments", "environment"} & parameters.keys():
            raise ValueError("Use Spawner.cmd, Spawner.args and Spawner.environment")
        if parameters.keys() - (
            JobSpec.model_fields.keys() - {"additional_properties"}
        ):
            raise ValueError("job_parameters contains unsupported IRI JobSpec fields")
        # The API submission environment is not the Hub/user job environment.
        parameters.setdefault("inherit_environment", False)
        spec = JobSpec(
            **parameters,
            executable=self.batchspawner_singleuser_cmd,
            arguments=[*self.cmd, *self.get_args()],
            environment=self.get_env(),
        )
        # A cancelled Hub start must still collect a successful submission's ID
        # before Hub cleanup calls stop(). Worker threads cannot be cancelled.
        task = asyncio.create_task(self._call("launch_job", job_spec=spec))
        cancelled = False
        try:
            job = await asyncio.shield(task)
        except asyncio.CancelledError:
            cancelled = True
            job = await task
        if not job.id:
            raise RuntimeError("IRI submission returned no job identifier")
        self.job_id = job.id
        self.job_status = "new"
        self._exit_code = None
        # Persist just the durable identity immediately, even while still queued.
        self.orm_spawner.state = self.get_state()
        self.db.commit()
        self.log.info("IRI job submitted")
        if cancelled:
            raise asyncio.CancelledError
        return self.job_id

    async def query_job_status(self):
        if not self.job_id:
            return JobStatus.NOTFOUND
        job = await self._call(
            "get_job", job_id=self.job_id, historical=True, include_spec=False
        )
        if job is None:
            self.job_status = "notfound"
            self._exit_code = 1
            return JobStatus.NOTFOUND
        if job.id != self.job_id:
            raise RuntimeError("IRI query returned a different job identifier")
        # Retain only normalized state and exit code, never raw IRI responses.
        self.job_status = job.status.state.value if job.status else "unknown"
        self._exit_code = job.status.exit_code if job.status else None
        if self.state_isrunning():
            return JobStatus.RUNNING
        if self.state_ispending():
            return JobStatus.PENDING
        if self.state_isunknown():
            return JobStatus.UNKNOWN
        return JobStatus.NOTFOUND

    def state_ispending(self):
        return self.job_status in ("new", "queued", "held")

    def state_isrunning(self):
        return self.job_status == "active"

    def state_isunknown(self):
        return self.job_status == "unknown"

    def state_gethost(self):
        # The launcher reports ip before batchspawner-singleuser reports port.
        # This remains correct whether the callback precedes or follows the
        # transition to ACTIVE in BatchSpawnerBase.start().
        return self.ip

    async def start(self):
        endpoint = await super().start()
        if endpoint[0] in ("", "0.0.0.0", "::") or endpoint[1] <= 0:
            raise RuntimeError(
                "The single-user launcher did not report a usable endpoint"
            )
        return endpoint

    async def poll(self):
        if not self.job_id:
            return 0
        status = await self.query_job_status()
        if status != JobStatus.NOTFOUND:
            return None
        code = self._exit_code
        if code is None:
            code = 0 if self.job_status in ("completed", "canceled") else 1
        self.clear_state()
        return code

    async def cancel_batch_job(self):
        if self.job_id:
            await self._call("cancel_job", job_id=self.job_id)

    async def stop(self, now=False):
        if not self.job_id:
            return
        await self.cancel_batch_job()
        if now:
            return
        # A 204 acknowledges cancellation; queued/held jobs may still exist.
        # The base stop() treats PENDING as stopped, so confirm terminal state.
        deadline = asyncio.get_running_loop().time() + self.stop_timeout
        while asyncio.get_running_loop().time() < deadline:
            if await self.poll() is not None:
                return
            await asyncio.sleep(self.startup_poll_interval)
        raise RuntimeError(
            "IRI cancellation is not yet confirmed; job identity retained"
        )

    def get_state(self):
        state = super().get_state()
        if self.job_id:
            state["iri_context"] = deepcopy(self._iri_context)
            state["iri_endpoint"] = {"ip": self.ip, "port": self.port}
        return state

    def load_state(self, state):
        super().load_state(state)
        self._iri_context = deepcopy(state.get("iri_context", {}))
        endpoint = state.get("iri_endpoint", {})
        self.ip = endpoint.get("ip", self.ip)
        self.port = endpoint.get("port", self.port)

    def clear_state(self):
        super().clear_state()
        self._iri_context = {}
        self._exit_code = None
