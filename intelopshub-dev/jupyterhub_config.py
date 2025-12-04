import os, pwd, globus_sdk
import jupyterhub
from tornado.log import app_log
from oauthenticator.globus import GlobusOAuthenticator

GLOBUS_COLLECTION = '17c583ac-6033-446c-80df-8f44c006cd47'
GLOBUS_OAUTH_CLIENT_ID = '32afb24a-ca13-491e-8b8c-063de6fdf57c'
GLOBUS_OAUTH_SECRET = os.environ['GLOBUS_OAUTH_SECRET'].strip()

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
    make_dir = True
    try:
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
            user_info = auth_client.userinfo()
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

#########################################
## Ex 4.2: Update jupyterhub_config.py ##
#########################################
c.JupyterHub.bind_url = 'http://127.0.0.1:8000/jhub/'
c.JupyterHub.hub_ip = '172.31.48.143'
c.JupyterHub.pid_file = '/var/run/jupyterhub.pid'

##########################################################
# Ex 10.2: Update jupyterhub_config.py for Globus Auth   #
##########################################################

c.JupyterHub.authenticator_class = GlobusOAuthenticator
c.GlobusOAuthenticator.oauth_callback_url = \
    'https://intelopshub-dev.american-science-cloud.org/jhub/hub/oauth_callback'
c.GlobusOAuthenticator.enable_auth_state = True
c.GlobusOAuthenticator.identity_provider = 'anl.gov'
c.GlobusOAuthenticator.client_id = GLOBUS_OAUTH_CLIENT_ID
c.GlobusOAuthenticator.client_secret = GLOBUS_OAUTH_SECRET
c.GlobusOAuthenticator.create_system_users = False
c.GlobusOAuthenticator.revoke_tokens_on_logout = False
c.GlobusOAuthenticator.exclude_tokens = []
c.GlobusOAuthenticator.scope = ['openid', 'profile', 'urn:globus:auth:scope:groups.api.globus.org:view_my_groups_and_memberships']

c.GlobusOAuthenticator.allowed_globus_groups = {'c4ee226d-d120-11f0-9aff-0e7d9e9fc9e3'}
c.GlobusOAuthenticator.admin_globus_groups = {'660f93c3-d121-11f0-b466-0affe2d2f23d'}

c.GlobusOAuthenticator.globus_local_endpoint = GLOBUS_COLLECTION
c.Spawner.environment = {'GLOBUS_COLLECTION': GLOBUS_COLLECTION}

c.Authenticator.post_auth_hook = user_setup

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