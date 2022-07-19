#!/bin/bash

# script to be run as run via cron
# checks for changes to config file and deploys if needed
# pulls repo
# diffs deployed config vs. config in repo
# if different
#   copy repo config to /etc/jupyterhub
#   restart jupyterhub to load new config

LOCK_FILE=/var/run/jupyterhub-config-update.lock
LOG_FILE=/var/log/jupyterhub-config-update.log
if [ -f "$LOCK_FILE" ]; then
  echo "Previous update failed, exiting"
  exit 1
fi

echo "$(date) JupyterHub config update check" > $LOCK_FILE
echo "$(date) JupyterHub config update check" >> $LOG_FILE

repo_dir=/home/ubuntu/jupyterhub-config-pull-only
repo_config=$repo_dir/config/jupyterhub_config.py
prod_config=/etc/jupyterhub/jupyterhub_config.py
repo_welcome=$repo_dir/Welcome.md
prod_welcome=/usr/local/share/jupyterhub/workshop/Welcome.md
repo_overrides=$repo_dir/overrides.json
prod_overrides=/usr/local/share/jupyterhub/workshop/overrides.json
repo_templates_dir=$repo_dir/templates
prod_templates_dir=/usr/local/share/jupyterhub/workshop/templates

runuser -u ubuntu -- git -C $repo_dir pull origin main

cp -f $repo_welcome $prod_welcome
chmod -wx $prod_welcome
cp -f $repo_overrides $prod_overrides
chmod -wx $prod_overrides
cp -rf $repo_templates_dir/*.html $prod_templates_dir
chmod -wx $prod_templates_dir/*

cmp -s $repo_config $prod_config
if [ $? -ne 0 ]; then
    echo "$(date) config changed, deploying" >> $LOG_FILE
    cp $prod_config $prod_config.bak
    cp $repo_config $prod_config
    service jupyterhub restart
    sleep 5
    service jupyterhub status
    if [ $? -eq 0 ]; then
	echo "$(date) update successful, hub running" >> $LOG_FILE
	rm -f $LOCK_FILE
    else
	# update failed, leave lock file
	echo "$(date) service restart failure, rolling back config" >> $LOG_FILE
	cp $prod_config.bak $prod_config
	service jupyterhub restart
	service jupyterhub status
	if [ $? -eq 0 ]; then
	    echo "$(date) rollback successful, hub running" >> $LOG_FILE
	else
	    echo "$(date) rollback failed, hub not running" >> $LOG_FILE
	fi
    fi
else
    echo "$(date) no changes to config" >> $LOG_FILE
    rm -f $LOCK_FILE
fi
