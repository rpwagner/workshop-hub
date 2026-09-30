# IRI BatchSpawner prototype

`IRIBatchSpawner` subclasses upstream `BatchSpawnerBase`. It replaces scheduler
submission/query/cancellation with the maintained `amsc-iri` generated client.
This directory is independent of the DockerSpawner deployments elsewhere in
this repository. It needs no Workshop Hub hostname, collection, Docker setup,
POSIX account on the Hub, or workshop data layout.

## Install in a separate Hub and execution environment

From a checkout, install into the **separate Hub's** Python environment:

```sh
python -m pip install './examples/iri_batchspawner[example]'
python -c 'from iri_batchspawner import IRIBatchSpawner; print(IRIBatchSpawner)'
```

Install the same directory into the **remote notebook job's** environment:

```sh
python -m pip install ./examples/iri_batchspawner
```

This supplies `iri-batchspawner-singleuser`, which delegates to upstream
`batchspawner-singleuser`. The remote environment also needs
`jupyterhub-singleuser` and a notebook server (e.g. JupyterLab). Match the Hub's
JupyterHub version in that environment. The small local package exists to
exercise installation and provide the launcher entry point; no publication is
required. It can be copied out of this repository and installed by itself.

Start with [`jupyterhub_config.py`](jupyterhub_config.py) in your own Hub
configuration. Supply its environment variables through deployment configuration
and secret management. Choose resource UUID, queue, account, duration in seconds,
node count, remote working/output paths, executable paths, Globus client,
identity provider and allowed groups locally. If users need different paths or
allocations, set `job_parameters` using the existing Hub `pre_spawn_hook` or
profiles configuration. `Spawner.cmd`, `Spawner.args`, and `Spawner.environment`
provide the single-user command and environment; other IRI `JobSpec` fields go
in `job_parameters`. Do not put tokens in those settings or in user options.

The example deliberately does not change or load the existing deployment files.
Container selection, modules/launchers, resource policy, tunnels, routable host
names, TLS certificates and firewall rules are deployment responsibilities.

## Authentication

Each IRI operation reads
`await user.get_auth_state()` → `tokens[resource_server]` → `access_token` and
checks that its space-delimited `scope` includes all `required_scopes`. This is
the supported GlobusOAuthenticator representation, including when `poll` or
`stop` runs after a Hub restart without a new spawn/login. Alternatively, set
`token_provider(spawner)` to a synchronous or asynchronous function returning
the same token-info dictionary (`access_token`, `scope`). It must obtain the
current scoped user token through the Hub's authentication infrastructure.

At inspection on 2026-09-30, ALCF uses resource server
`6be511f6-a071-471f-9bc0-02a0d0836723` and scope
`https://auth.globus.org/scopes/6be511f6-a071-471f-9bc0-02a0d0836723/filesystem`
for its IRI service, including compute operations. Despite its name, this is
the scope registered in ALCF's official token client. The example config contains
this service registration; the reusable code has no ALCF constants. No filesystem
operations or Transfer scopes are needed by the spawner.

Enable `GlobusOAuthenticator.enable_auth_state` and supply
`JUPYTERHUB_CRYPT_KEY` to the Hub. The Hub owns encrypted auth-state storage,
OAuth consent, token refresh/replacement and reauthentication. The spawner has
no credential file, token cache or OAuth flow and never uses client credentials
for scheduler operations. It validates scope metadata locally; IRI enforces
actual authorization. Missing, expired, revoked or unauthorized tokens require
the authenticator/operator to restore user authorization. An IRI error retains
the tracked job; it is not interpreted as proof that the job exited.

GlobusOAuthenticator's `pre_spawn_start` puts a base64/pickled copy of **all**
auth state in `GLOBUS_DATA`, including `token_response`. `get_env()` filters
`GLOBUS_DATA` and `GLOBUS_LOCAL_ENDPOINT` from the job environment. Simply adding
IRI to `exclude_tokens` is insufficient because it also removes the token from
`auth_state['tokens']`, and `token_response` remains. The existing Workshop Hub
uses this forwarding for notebooks; the prototype does not forward it.

The remote launcher uses the normal per-server **JupyterHub** API token to
report its address. This is BatchSpawner's existing authentication boundary,
not the user's Globus token. API clients are constructed per operation with
HTTP debug disabled; response bodies and headers are not included in errors.
Do not enable third-party HTTP wire logging in deployment.

## API and lifecycle mapping

The prototype targets the deployed **IRI v1 compute contract**, checked against
ALCF's public OpenAPI, rather than assuming the evolving IRI v2 specification
has the same paths. `api_url` is an HTTPS service origin, e.g.
`https://iri.example.org`; `amsc-iri` supplies `/api/v1` paths. It does not accept
arbitrary URL prefixes or automatically translate v2 services.

| Operation | IRI v1 contract | Mapping |
| --- | --- | --- |
| Submit | `ComputeApi.launch_job(resource_id, JobSpec)` | Returns `Job.id` directly; not an asynchronous task ID |
| Query | `ComputeApi.get_job(resource_id, job_id, historical=True, include_spec=False)` | Reads `Job.status.state`, requests completed history |
| Cancel | `ComputeApi.cancel_job(resource_id, job_id)` | HTTP 204 acknowledges the request; normal stop polls until terminal |
| Endpoint | No standardized server-address field | Existing authenticated BatchSpawner callback reports host, then port |

| IRI state | BatchSpawner status | JupyterHub `poll()` |
| --- | --- | --- |
| `new`, `queued`, `held` | `PENDING` | `None` |
| `active` | `RUNNING` | `None` |
| No status yet | `UNKNOWN` | `None` |
| `completed` | `NOTFOUND` | Exit code, or 0 |
| `canceled` | `NOTFOUND` | Exit code, or 0 |
| `failed` | `NOTFOUND` | Exit code, or 1 |
| Query HTTP 404 | `NOTFOUND` | 1 |

With no tracked job, `poll()` returns 0. Other HTTP, transport or decoding errors
raise a redacted error and preserve job identity. Unknown enum values are rejected
by the maintained client; they are not silently mapped to a terminal state.
`stop(now=True)` sends cancellation and returns immediately; normal `stop()`
includes pending/held jobs in its bounded confirmation wait. A confirmation
timeout raises with the ID retained for retry/recovery.

The tiny launcher reports `socket.getfqdn()` to the existing `/hub/api/batchspawner`
handler before delegating to upstream's port allocator and single-user launcher.
It honors HubAuth's existing TLS settings. Set `IRI_JUPYTER_HOST` in the remote
launch environment if the execution hostname is not the proxy-reachable address.
The callback can precede or follow IRI's transition to `active`; startup waits
for the upstream port callback. An `active` job alone does not establish server
readiness. The Hub performs its usual HTTP readiness check afterward.

The Hub API must be reachable **from** the job, and the proxy must reach the
reported host/port. There is no new tunnel, filesystem rendezvous, scheduler CLI
or invented IRI metadata field. Verify those network paths on the intended site
before live acceptance. BatchSpawner 1.3.0 waits for the port until Hub
`start_timeout`; if a job dies before that callback, timeout triggers Hub cleanup.
Current upstream main adds polling during this wait. This prototype retains the
released base behavior rather than copying its start loop.

State contains only job ID, normalized job status, service/resource/auth-service
identifiers, required scope names and endpoint. The target context is retained
so a configuration change cannot redirect polling/cancellation of an old job
to a different resource. Submission immediately saves the ID in the Hub's
spawner state, before queue waiting; normal Hub state saving records the ready
endpoint. Response JobSpecs, metadata, messages and tokens are never serialized.
If Hub start is cancelled during submission, the bounded client call is allowed
to finish and its ID is captured before Hub cleanup. Automatic HTTP retries
are disabled: the deployed submit endpoint does not document idempotency.
A network loss after server-side submission but before delivery of its ID can
still require operator reconciliation; the API does not provide an atomic
transaction with the Hub database.

## Upstream inspection and dependencies

Inspected upstream main and the actual installed distributions before choosing
the overrides:

- [BatchSpawner extension/lifecycle/callback source](https://github.com/jupyterhub/batchspawner/tree/451dcf171cff7883904845d5de8c5e5e250b64d9): retain the base startup and handler; replace `submit_batch_script`, `query_job_status`, `cancel_batch_job`, state predicates and terminal poll/stop mapping. Tested with released 1.3.0.
- [GlobusOAuthenticator source](https://github.com/jupyterhub/oauthenticator/blob/9af1663d0b9d849a2acec5233c64a47e1762c71f/oauthenticator/globus.py) and [configuration documentation](https://oauthenticator.readthedocs.io/en/stable/api/gen/oauthenticator.globus.html): `tokens` is indexed by resource server; pre-spawn forwards auth state. Tested with 17.4.0.
- [ALCF deployed OpenAPI](https://api.alcf.anl.gov/openapi.json) and [official usage guide](https://docs.alcf.anl.gov/services/iri-api/): direct `Job` response, seven job states, historical query, 204 cancellation, optional environment/resources/attributes and backend-specific metadata.
- [Official ALCF token client](https://github.com/argonne-lcf/alcf-tokens/blob/main/src/alcf_tokens/auth.py): exact IRI registration above. The client itself is not used because it owns an independent login/token store.
- [DOE IRI client toolkit](https://github.com/doe-iri/iri-facility-api-toolkit/tree/1910b0701047dfb8c6a1a30ce33b4bd6dab12633) uses [`amsc-iri` 1.2.0](https://pypi.org/project/amsc-iri/1.2.0/). Use this lower-level generated client directly for typed job specs and all protocol operations. The orchestration toolkit's sessions and credential files are unnecessary here.

Dependencies are confined to this installable example. `requests` implements
the same Hub callback used upstream; it is not an IRI protocol client. No new
OAuth library, scheduler CLI, persistent credential abstraction or orchestration
layer is introduced. The local checks use JupyterHub 5.5.2.

## Synthetic checks

From the repository root:

```sh
python -m pip install './examples/iri_batchspawner[test]'
python -m pytest examples/iri_batchspawner/tests
python -m ruff check examples/iri_batchspawner
python -m ruff format --check examples/iri_batchspawner
git diff --check
```

Tests intercept the generated client's HTTP transport and exercise its real
serialization and response models, upstream startup, Globus auth-state creation
and forwarding, scoped token lookup/injection, all job states, cancellation,
restart state, callback ordering and redacted failures. They require no live
tokens, ALCF access or scheduler. The scoped CI workflow runs these checks;
the repository previously had only manually triggered image-build workflows.
Live login, resource launch and bidirectional network reachability remain
deployment acceptance tasks; they are not claimed by synthetic tests.
