# IntelOps Initial Dev Environment

The initial deployment of the IntelOps AWS dev account will contain JupyterHub and GCS to enable the development of custom Jupyter notebook environments and data sharing.

## AWS Resource Summary

- Region: `us-west-2`
- Two `t3.medium` EC2 instances, one for JupyterHub, one for GCS, both Ubuntu 24.04 LTS
- Two Elastic IP addresses, one per EC2 instance
- Two security groups:
  - GCS
    - Outbound: anywhere
    - Inbound: HTTPS, 50000 - 51000, SSH from 140.221.0.0/16 and 130.202.0.0/16 (Argonne)
  - JupyterHub
    - Outbound: anywhere
    - Inbound: HTTP, HTTPS, SSH from 140.221.0.0/16 and 130.202.0.0/16 (Argonne)
- An Elastic File System (EFS) configured to allow inbound NFS (`2049`) from GCS and JupyterHub security groups

An A record for the JupyterHub Elastic IP will be configured by Patrick in Route 53.

## EFS

The EFS file system is mounted on the GCS and JupyterHub instances over NFSv4 on `/data`. The folder `/data/jupyterhub` is owned by `ubuntu:ubuntu`.

## JupyterHub

The configuration of JupyterHub is intended to port easily into Zero-to-JupyterHub. The configuration is primarily captured in the `jupyterhub_config.py` file, which includes the auth configuration and selectable images. Other scripts are used to manage the JupyterHub service, which will not be needed in a Zero-to-JupyterHub deployment.

### Auth

JupyterHub will be configured to allow logins via Globus Auth, with acces restricted to members of defined Globus Groups. There will be a user and a JupyerHub admin group. Users will be added to the groups using their lab identities. These groups will be reused for access to data via GCS.

### Notebook Environment

A user's notebook environment will be launched using DockerSpawner, where the user can select from a defined set of images. The initial set will be based on the Jupyter released images. One of the first tasks will be to establish a basic CI/CD process to enable a customized notebook environment.

### Notebook Data

The home directory, `/home/jovyan`, can be written to, but is not persistent.

`/home/jovyan/work/` is the default directory for the notebook server
and is the root in the JupyterLab file manager. There is also the
line `cd ~/work` in the Bash configuration so that when a terminal is
opened the user goes straight there. This folder is bind mounted from
the user's folder in the Globus collection.

The `/public-data/` folder from the Globus collection is bind
mounted read-only at `/home/jovyan/work/public-data/`.

The `/shared-data/` folder from the Globus collection is bind
mounted read-write at `/home/jovyan/work/shared-data/`.

| Folder or File     | Permissions | Persistent | Globus | Path
| ----------- | ----------- | ------ | ----- |
| `/home/jovyan` | RW | No | No | N/A |
| `/home/jovyan/work` | RW | Yes | Yes, at `/{username}/` | `/data/jupyterhub/{username}` |
| `/home/jovyan/work/public-data` | RO | Yes | Yes, at `/public-data/` | `/data/jupyterhub/public-data` |
| `/home/jovyan/work/shared-data` | RW | Yes | Yes, at `/shared-data/` | `/data/jupyterhub/shared-data` |

When a user first logs into JupyterHub, the folder `/data/jupyterhub/{username}` is created and the user is granted read-write permission to it in the Guest Collection.

## GCS

The GCS setup is the standard installation with a private mapped collection rooted at `/data`. The identity mapping will be set to map an ANL IntelOps admin to `ubuntu` (this can be adjusted).

A separate Guest Collection will be created to allow users to access data that will be rooted at `/data/jupyterhub`. In the Guest Collection, the same read-write rules as above apply, with the exception that admins will be able to write to the `/shared-data` folder. 

## Setup

DNS intelopshub-dev.americansciencecloud.org

### Globus Groups

- AmSC IntelOps Dev Users c4ee226d-d120-11f0-9aff-0e7d9e9fc9e3
- AmSC IntelOps Dev Admins 660f93c3-d121-11f0-b466-0affe2d2f23d

### Globus Auth

JupyterHub Client: `32afb24a-ca13-491e-8b8c-063de6fdf57c`
Identity: `32afb24a-ca13-491e-8b8c-063de6fdf57c@clients.auth.globus.org`
Redirect: `https://intelopshub-dev.american-science-cloud.org/jhub/hub/oauth_callback`
