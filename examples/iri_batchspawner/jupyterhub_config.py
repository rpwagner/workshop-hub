"""Example for a separate Hub; all allocation/network/identity policy is local."""

import os

from oauthenticator.globus import GlobusOAuthenticator

from iri_batchspawner import IRIBatchSpawner

c = get_config()  # noqa: F821 - supplied by JupyterHub's configuration loader

# Current ALCF IRI service registration. These choices belong in deployment
# configuration, not IRIBatchSpawner. Other IRI v1 services can supply their own.
iri_resource_server = "6be511f6-a071-471f-9bc0-02a0d0836723"
iri_scope = f"https://auth.globus.org/scopes/{iri_resource_server}/filesystem"
groups_scope = (
    "urn:globus:auth:scope:groups.api.globus.org:view_my_groups_and_memberships"
)

c.JupyterHub.authenticator_class = GlobusOAuthenticator
c.GlobusOAuthenticator.client_id = os.environ["GLOBUS_CLIENT_ID"]
c.GlobusOAuthenticator.client_secret = os.environ["GLOBUS_CLIENT_SECRET"]
c.GlobusOAuthenticator.oauth_callback_url = os.environ["GLOBUS_CALLBACK_URL"]
c.GlobusOAuthenticator.identity_provider = os.environ["HUB_IDENTITY_PROVIDER"]
c.GlobusOAuthenticator.enable_auth_state = True
# JUPYTERHUB_CRYPT_KEY must be supplied to the Hub by deployment secret management.
c.GlobusOAuthenticator.scope = ["openid", "profile", groups_scope, iri_scope]
c.GlobusOAuthenticator.allowed_globus_groups = set(
    os.environ["HUB_ALLOWED_GLOBUS_GROUPS"].split()
)
c.GlobusOAuthenticator.exclude_tokens = ["auth.globus.org", "groups.api.globus.org"]
# Do not add IRI to exclude_tokens: it also removes IRI from auth_state['tokens'].
# The spawner reads auth_state['tokens'][iri_resource_server]['access_token']
# afresh on each API operation. It filters GLOBUS_DATA out of the remote env.
c.GlobusOAuthenticator.revoke_tokens_on_logout = False

c.JupyterHub.spawner_class = IRIBatchSpawner
c.IRIBatchSpawner.api_url = "https://api.alcf.anl.gov"
c.IRIBatchSpawner.resource_server = iri_resource_server
c.IRIBatchSpawner.required_scopes = [iri_scope]
c.IRIBatchSpawner.resource_id = os.environ["IRI_RESOURCE_ID"]
c.IRIBatchSpawner.job_parameters = {
    "name": "jupyterhub",
    "directory": os.environ["IRI_JOB_DIRECTORY"],
    "stdout_path": os.environ["IRI_STDOUT_PATH"],
    "stderr_path": os.environ["IRI_STDERR_PATH"],
    "resources": {"node_count": int(os.environ["IRI_NODE_COUNT"])},
    "attributes": {
        "queue_name": os.environ["IRI_QUEUE"],
        "account": os.environ["IRI_ACCOUNT"],
        "duration": int(os.environ["IRI_DURATION_SECONDS"]),
        # Add custom_attributes (e.g. filesystems), container, pre_launch or
        # launcher here if the selected resource's deployment requires them.
    },
}
# Both commands must be installed in the remote job's environment. Absolute
# paths are useful when the resource does not add that environment to PATH.
c.IRIBatchSpawner.batchspawner_singleuser_cmd = os.environ["IRI_SINGLEUSER_WRAPPER"]
c.Spawner.cmd = [os.environ["IRI_SINGLEUSER_COMMAND"]]
c.Spawner.start_timeout = 600
c.Spawner.http_timeout = 120
c.JupyterHub.cleanup_servers = False
c.JupyterHub.hub_bind_url = os.environ["HUB_BIND_URL"]
c.JupyterHub.hub_connect_url = os.environ["HUB_CONNECT_URL"]
# The Hub API must be reachable from the job, and the proxy must reach the
# reported compute hostname/port. Supply existing site routing outside this
# backend. If getfqdn() is unsuitable, pre_launch can export IRI_JUPYTER_HOST.
