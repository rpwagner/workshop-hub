import os
import jupyterhub
from oauthenticator.globus import LocalGlobusOAuthenticator

c.Application.log_level = 'DEBUG'

#########################################
## Ex 4.2: Update jupyterhub_config.py ##
#########################################
c.JupyterHub.bind_url = 'http://127.0.0.1:8000/jhub/'
c.JupyterHub.hub_ip = '172.31.21.55'
c.JupyterHub.pid_file = '/var/run/jupyterhub.pid'

# ####################################################
# Ex 6.2: Update jupyterhub_config.py with Alt Names #
# ####################################################
# c.JupyterHub.trusted_alt_names = ['DNS:trainXX.jupyter-security.info', 'DNS:trainXX']
# c.JupyterHub.internal_certs_location = '/etc/jupyterhub/internal-ssl'
# c.JupyterHub.internal_ssl = True

#################################################################
# Ex 8.3: Update jupyterhub_config.py with IPC Kernel Transport #
#################################################################
# c.Spawner.args = ['--transport="ipc"']

##########################################################
# Ex 10.2: Update jupyterhub_config.py for Globus Auth   #
##########################################################

c.Authenticator.allowed_users = {"rpwagner"}

GLOBUS_OAUTH_CLIENT_ID = '57f6522e-bfc6-451d-823e-1bf36f89291b'
GLOBUS_OAUTH_SECRET = os.environ['GLOBUS_OAUTH_SECRET'].strip()

c.JupyterHub.authenticator_class = LocalGlobusOAuthenticator
c.LocalGlobusOAuthenticator.oauth_callback_url = \
    'https://jupyterhub.rickwagner.io/jhub/hub/oauth_callback'
c.LocalGlobusOAuthenticator.enable_auth_state = True
c.LocalGlobusOAuthenticator.identity_provider = 'github.com'
c.LocalGlobusOAuthenticator.client_id = GLOBUS_OAUTH_CLIENT_ID
c.LocalGlobusOAuthenticator.client_secret = GLOBUS_OAUTH_SECRET
c.LocalGlobusOAuthenticator.create_system_users = False
c.LocalGlobusOAuthenticator.revoke_tokens_on_logout = True
c.LocalGlobusOAuthenticator.scope = ['openid', 'profile']


c.JupyterHub.spawner_class = 'dockerspawner.DockerSpawner'

c.DockerSpawner.allowed_images = {'Base Single User Notebook': 'quay.io/jupyterhub/singleuser:5.4.2',
    'SciPy Notebook': 'quay.io/jupyter/scipy-notebook:hub-5.4.2'}

c.DockerSpawner.remove = True
c.DockerSpawner.start_timeout = 180
c.DockerSpawner.pull_policy = 'always'

c.DockerSpawner.notebook_dir = '/home/jovyan/work'

c.DockerSpawner.volumes = { '/data/hub/{username}': {"bind": '/home/jovyan/work', "mode": "rw"},
                            '/data/hub/public-data': {"bind": '/home/jovyan/work/public-data', "mode": "ro"},
                            '/data/hub/shared-data': {"bind": '/home/jovyan/work/shared-data', "mode": "rw"}
                            }

c.DockerSpawner.args = ['--FileCheckpoints.checkpoint_dir=/home/jovyan/work/.ipynb_checkpoints',]
c.DockerSpawner.post_start_cmd = 'sh -c \'echo "cd ~/work" >> /home/jovyan/.bashrc\''