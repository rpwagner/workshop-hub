import os, pwd, globus_sdk
import jupyterhub
from tornado.log import app_log
from oauthenticator.globus import GlobusOAuthenticator


GLOBUS_COLLECTION = '<your collection UUID>'
GLOBUS_OAUTH_CLIENT_ID = '<your OAuth Client ID>'
GLOBUS_OAUTH_SECRET = os.environ['GLOBUS_OAUTH_SECRET'].strip()

SKIP_MKDIR = ('nobody',)

def user_setup(authenticator, handler, authentication):
    user_name = authentication['name']
    globus_client = globus_sdk.ConfidentialAppAuthClient(
        c.GlobusOAuthenticator.client_id,
	c.GlobusOAuthenticator.client_secret)
    tokens = globus_client.oauth2_client_credentials_tokens(
    requested_scopes='urn:globus:auth:scope:transfer.api.globus.org:all')
    transfer_token_info = ( 
    			tokens.by_resource_server["transfer.api.globus.org"])
    transfer_token = transfer_token_info["access_token"]
    transfer_client = globus_sdk.TransferClient(
    		    authorizer=globus_sdk.AccessTokenAuthorizer(transfer_token))
    if user_name in SKIP_MKDIR:
        make_dir = False
    else:
        make_dir = True
        try:
            transfer_client.endpoint_autoactivate(GLOBUS_COLLECTION)
            listing = transfer_client.operation_ls(GLOBUS_COLLECTION,
                                                       path='/')
            for i in listing:
                if i['type'] == 'dir' and i['name'] == user_name:
                    make_dir = False
                    break
        except:
            app_log.warning('error on ls, collection {}, path {}'.format(GLOBUS_COLLECTION, '/'))
    if make_dir:
        collection_path = '/{}/'.format(user_name)
        try:
            mkdir_result = transfer_client.operation_mkdir(GLOBUS_COLLECTION, path=collection_path)
        except:
            app_log.warning('error on mkdir, collection {}, path {}'.format(GLOBUS_COLLECTION, collection_path))
        try:
            auth_token = authentication['auth_state']['tokens']['auth.globus.org']['access_token']
            auth_client = globus_sdk.AuthClient(
    		    authorizer=globus_sdk.AccessTokenAuthorizer(auth_token))
            user_info = auth_client.oauth2_userinfo()
            user_identity = user_info['sub']
            rule_data = {
                'DATA_TYPE': 'access',
                'permissions': 'rw',
                'principal' : user_identity,
                'principal_type' : 'identity',  
                'path': collection_path
                }

            response = transfer_client.add_endpoint_acl_rule(GLOBUS_COLLECTION, rule_data)
            access_rule_id = response['access_id']
            app_log.debug('access rule id {} for created user name {}, identity {}, collection {}, path {}'.format(access_rule_id, user_name,
                                                                                                           user_identity, GLOBUS_COLLECTION, collection_path))
        except:
            app_log.warning('failed to created access rule created for user name {}, collection {}, path {}'.format(user_name, GLOBUS_COLLECTION, collection_path))
    return authentication


c.Application.log_level = 'DEBUG'

c.JupyterHub.bind_url = 'http://127.0.0.1:8000/jhub/'
c.JupyterHub.hub_ip = '<your hub ip>'
c.JupyterHub.pid_file = '/var/run/jupyterhub.pid'

c.JupyterHub.cleanup_servers = False

c.JupyterHub.template_paths = ['/usr/local/share/jupyterhub/workshop/templates',]
c.JupyterHub.template_vars = {'workshopname': 'A Data-Enabled Workshop',
                                  'studentgroup': 'StudentGroupUUID'}

c.JupyterHub.authenticator_class = GlobusOAuthenticator
c.GlobusOAuthenticator.enable_auth_state = True
c.GlobusOAuthenticator.oauth_callback_url = \
 '<your callback URL>'
c.GlobusOAuthenticator.identity_provider = ''
c.GlobusOAuthenticator.client_id = GLOBUS_OAUTH_CLIENT_ID
c.GlobusOAuthenticator.client_secret = GLOBUS_OAUTH_SECRET
c.GlobusOAuthenticator.create_system_users = False
c.GlobusOAuthenticator.revoke_tokens_on_logout = False
c.GlobusOAuthenticator.exclude_tokens = []
# Groups of allowed users
c.GlobusOAuthenticator.allowed_globus_groups = {'<your allowed group>',
                                                   '<your admin group>'}
# Admin users
c.GlobusOAuthenticator.admin_globus_groups = {'<your admin group>'}

c.GlobusOAuthenticator.globus_local_endpoint = GLOBUS_COLLECTION
c.Spawner.environment = {'GLOBUS_COLLECTION': GLOBUS_COLLECTION}

c.Authenticator.post_auth_hook = user_setup

c.JupyterHub.spawner_class = 'dockerspawner.DockerSpawner'

_jupyterhub_xyz = "%i.%i.%i" % (jupyterhub.version_info[:3])
_jupyterhub_xy = "%i.%i" % (jupyterhub.version_info[:2])
singleuser_image = "jupyterhub/singleuser:%s" % _jupyterhub_xy
datascience_image = "jupyter/datascience-notebook:hub-%s" % _jupyterhub_xyz
r_image = "jupyter/r-notebook:hub-%s" % _jupyterhub_xyz
spatialtx_image = "brianyee/spatial-tx:hub-2.2.2"
spatialtx_image_latest = "brianyee/spatial-tx:latest"
c.DockerSpawner.allowed_images = { 'CSHL Single Cell Analysis Notebook': spatialtx_image,
                                   'Datascience Notebook': datascience_image,
                                   'R Notebook': r_image ,
                                   'Base Single User Notebook' : singleuser_image,
				  'Test Image': spatialtx_image_latest}

c.DockerSpawner.remove = True

c.DockerSpawner.notebook_dir = '/home/jovyan/work'
c.DockerSpawner.volumes = { '/data/workshop/{username}': {"bind": '/home/jovyan/work', "mode": "rw"},
                            '/usr/local/share/jupyterhub/workshop/Welcome.md': {"bind": '/home/jovyan/work/Welcome.md', "mode": "ro"},
                            '/data/workshop/public-data': {"bind": '/home/jovyan/work/public-data', "mode": "ro"},
                            '/data/workshop/shared-data': {"bind": '/home/jovyan/work/shared-data', "mode": "rw"},
                            '/usr/local/share/jupyterhub/workshop/overrides.json': {"bind": '/opt/conda/share/jupyter/lab/settings/overrides.json', "mode": "ro"}
                                }

c.DockerSpawner.start_timeout = 180
c.DockerSpawner.pull_policy = 'always'
c.DockerSpawner.args = ['--FileCheckpoints.checkpoint_dir=/home/jovyan/work/.ipynb_checkpoints',]
c.DockerSpawner.post_start_cmd = 'sh -c \'echo "cd ~/work" >> /home/jovyan/.bashrc\''
