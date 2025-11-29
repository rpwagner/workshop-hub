# JupyterHub Setup

## Create a User

```
sudo adduser --disabled-password --gecos 'rpwagner' rpwagner
```

## Basic Install

```
sudo timedatectl set-timezone America/Los_Angeles
```

```
sudo apt-get install emacs-nox certbot apache2 python3-certbot-apache nodejs npm docker.io
```

```
sudo npm install -g configurable-http-proxy
```

```
sudo mkdir /usr/local/miniconda
```

```
wget -nv -O /tmp/Miniconda3-latest-Linux-x86_64.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
```

```
sudo sh /tmp/Miniconda3-latest-Linux-x86_64.sh -b -f -p /usr/local/miniconda
```

```
sudo /usr/local/miniconda/bin/python3 -m pip install --root-user-action=ignore notebook jupyterhub globus_sdk oauthenticator jupyterlab dockerspawner
```

## HTTPS Certificates

```
sudo hostnamectl set-hostname jupyterhub.rickwagner.io
```

```
sudo systemctl daemon-reload
```

```
sudo a2enmod ssl rewrite proxy proxy_http proxy_wstunnel headers
```

```
sudo systemctl restart apache2.service
```

```
sudo certbot -n -d jupyterhub.rickwagner.io --apache --agree-tos --email rick@rickwagner.io
```

```
sudo systemctl restart apache2.service
```

## Setup JupyterHub

```
sudo mkdir /etc/jupyterhub
```

```
(umask 066; touch /tmp/js; openssl rand -hex 32 > /tmp/js)
```

```
sudo mv /tmp/js /etc/jupyterhub/jupyterhub_cookie_secret
```

```
(umask 066; touch /tmp/ck; openssl rand -hex 32 > /tmp/ck)
```

```
sudo mv /tmp/ck /etc/jupyterhub/crypt.key
```

```
(umask 066; touch /tmp/gos; echo {secret} > /tmp/gos)
```

```
sudo mv /tmp/gos /etc/jupyterhub/globus-oauth-secret.txt
```

SCP files to server

```
sudo cp jupyterhub.sh /etc/jupyterhub/jupyterhub.sh
```

```
sudo chmod u+x /etc/jupyterhub/jupyterhub.sh
```

```
sudo cp jupyterhub.service /etc/jupyterhub/jupyterhub.service
```

```
sudo cp jupyterhub_config.py /etc/jupyterhub/jupyterhub_config.py
```

```
sudo cp 000-default-le-ssl.conf /etc/apache2/sites-available/000-default-le-ssl.conf 
```

```
sudo systemctl restart apache2.service
```


```
sudo chmod -R go-w /etc/jupyterhub
```

```
sudo cp /etc/jupyterhub/jupyterhub.service /etc/systemd/system/jupyterhub.service
```

```
sudo systemctl enable jupyterhub.service
```

```
sudo systemctl start jupyterhub.service
```

## Globus OAuth

Client: `57f6522e-bfc6-451d-823e-1bf36f89291b`

```
c.LocalGlobusOAuthenticator.oauth_callback_url = \
    'https://jupyterhub.rickwagner.io/jhub/hub/oauth_callback'
```
