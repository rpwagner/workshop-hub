# For Mike

For classes and workshops I build JupyterHub servers using:
- Miniconda Python distribution for the base JupyterHub service
- Stable DNS entry for the server
- Let’s Encrypt certificate
- Globus OAuthenticator tied to GitHub or another single IdP to define a specific namespace for the usernames
- Globus Groups as part of the Globus OAuthenticator configuration to define users and admins
- DockerSpawner to run the user notebook environments
  - This avoids needing to create POSIX accounts for every user on the servers
  - Custom images can be built on top of container images maintained by Jupyter
  - Directories can be mounted read-write or read-only into a pod using bind mounts defined in the DockerSpawner configuration
- NFS export to hold home directories, reference data, and workspaces
- Globus Guest Collection
  - Backed by the NFS export
  - Provides Globus & HTTPS access to the directories described above
  - Data access rules following the same policies as what users and see and do when logged into JupyterHub
  - Per-user directories are created when a user first logs into JupyterHub

See [References](#references) below for links to the documentation for these.

## Setup

See [`jupyterhub.md`](jupyterhub.md) for the steps I last used to setup a JuptyerHub server. Many of the files referenced are in the [`config/`](config/) directory.

Make sure to update the hostname in [`000-default-le-ssl.conf`](config/apache2/000-default-le-ssl.conf).

### `jupyterhub_config.py`

This is the file where most of the work happens. I’ve posted a minimal (untested) one below that assumes no Globus Guest Collection and no DockerSpawner. There are several examples in this repo, with [`jupyterhub.rickwagner.io/jupyterhub_config.py`](./jupyterhub.rickwagner.io/jupyterhub_config.py) being the latest.

- Look for the line with `c.JupyterHub.hub_ip`, if the server has a private IP address that handles traffic to the Internet, such as on an EC2 instance this needs to be set. Probably also needs to be set if the server has more than one IP.
- If `c.GlobusOAuthenticator.create_system_users` is true, it will cause a new POSIX user account to be created whenever someone logs in who doesn’t have one. This is useful when the users are managed via a Globus Group and all their usernames are tied to a single identity provider.
- `c.GlobusOAuthenticator.identity_provider` probably needs to be `uic.edu` for your use case. Follow the instructions on the Globus OAuthenticator to make sure the usernames all come from only `uic.edu`

```
from oauthenticator.globus import GlobusOAuthenticator

GLOBUS_OAUTH_CLIENT_ID = '<your-client-id>'
GLOBUS_OAUTH_SECRET = os.environ['GLOBUS_OAUTH_SECRET'].strip()

c.Application.log_level = 'DEBUG'

c.JupyterHub.bind_url = 'http://127.0.0.1:8000/jhub/'
c.JupyterHub.hub_ip = '172.31.21.55'
c.JupyterHub.pid_file = '/var/run/jupyterhub.pid'

c.JupyterHub.authenticator_class = GlobusOAuthenticator
c.GlobusOAuthenticator.oauth_callback_url = \
    'https://jupyterhub.rickwagner.io/jhub/hub/oauth_callback'
c.GlobusOAuthenticator.enable_auth_state = True
c.GlobusOAuthenticator.identity_provider = 'github.com'
c.GlobusOAuthenticator.client_id = GLOBUS_OAUTH_CLIENT_ID
c.GlobusOAuthenticator.client_secret = GLOBUS_OAUTH_SECRET
c.GlobusOAuthenticator.create_system_users = True
c.GlobusOAuthenticator.revoke_tokens_on_logout = False
c.GlobusOAuthenticator.exclude_tokens = []
c.GlobusOAuthenticator.scope = ['openid', 'profile', 'urn:globus:auth:scope:groups.api.globus.org:view_my_groups_and_memberships']

c.GlobusOAuthenticator.allowed_globus_groups = {'<your-user-group-uuid>'}
c.GlobusOAuthenticator.admin_globus_groups = {'<your-admin-group-uuid>'}
```

## References

- [JupyterHub](https://jupyterhub.readthedocs.io/en/stable/)
- [The Littlest JupyterHub](https://tljh.jupyter.org/en/latest/) (TLJH)
  - [How to Guides](https://tljh.jupyter.org/en/latest/howto/index.html), these are useful on many JupyterHub deployments
- [Globus OAuthenticator](https://oauthenticator.readthedocs.io/en/latest/tutorials/provider-specific-setup/providers/globus.html)
  - [User Identity](https://oauthenticator.readthedocs.io/en/latest/tutorials/provider-specific-setup/providers/globus.html#user-identity) has details on getting the right username based on a single IdP
  - [Group Management](https://oauthenticator.readthedocs.io/en/latest/tutorials/provider-specific-setup/providers/globus.html#group-management) describes how to use Globus Groups to define users and admins
- [DockerSpawner](https://jupyterhub-dockerspawner.readthedocs.io/en/latest/index.html)
  - [Data and mounts](https://jupyterhub-dockerspawner.readthedocs.io/en/latest/data-persistence.html)
  - [Container images](https://jupyterhub-dockerspawner.readthedocs.io/en/latest/docker-image.html)
