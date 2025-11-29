# workshop-hub

Data-Enabled JupyterHub Example

## EC2

- Get PEM file
- Security Groups
  - GCS
    - Outbound anywhere
    - Inbound: HTTPS, 50000 - 51000, SSH
  - JupyterHub
    - Outbound anywhere
    - Inbound: HTTP, HTTPS, SSH
    
## Setup GCS

- `t3.medium`
- Instance `i-0d1753bd8f74c566b`
-  Elastic IP `44.224.205.200`
- `172.31.22.24`
- update, upgrade, reboot
- [Quickstart Install](https://docs.globus.org/globus-connect-server/v5.4/quickstart/)

```
globus-connect-server endpoint setup "Rick JupyterHub GCS Server" \
    --organization "Rick Wagner Testing" \
    --owner rpwagner@github.com \
    --contact-email rick@rickwagner.io
```

```
Created endpoint 873e22af-f841-49d4-ab40-fc2c1cafbf4d
Endpoint domain_name 23095d.69a6.gaccess.io
No subscription is set on this endpoint, so only basic features are enabled.


To enable subscription features on this endpoint, you must associate your
subscription with this endpoint. If you are not a member of a subscription
group, the Globus subscription manager for your organization can associate a
subscription to this endpoint for you.

If you plan on using the Google Drive or Google Cloud Storage
connectors, use
     https://23095d.69a6.gaccess.io/api/v1/authcallback_google
as the Authorized redirect URI for this endpoint
```

```
sudo globus-connect-server node setup
```

```
globus-connect-server login localhost
```

```
(base) rpwagner@Mac ~ %  globus login --gcs 873e22af-f841-49d4-ab40-fc2c1cafbf4d
(base) rpwagner@Mac ~ % globus gcs endpoint set-subscription-id 873e22af-f841-49d4-ab40-fc2c1cafbf4d 6cb69fd5-a845-11e7-aeab-22000a92523b
Updated Endpoint 873e22af-f841-49d4-ab40-fc2c1cafbf4d
```

```
globus-connect-server storage-gateway create posix "POSIX Gateway" --domain 'github.com'
Storage Gateway ID: efddba38-48ea-4302-84da-21d4aa0f98ac
```

```
globus-connect-server storage-gateway update posix efddba38-48ea-4302-84da-21d4aa0f98ac  --identity-mapping file:idmap.json 
Message: Updated Storage Gateway efddba38-48ea-4302-84da-21d4aa0f98ac
```

```
globus-connect-server collection create \
    efddba38-48ea-4302-84da-21d4aa0f98ac \
    /data/ \
    "Shared Data"
Collection ID: 3eccaccf-e99d-41a4-b115-4082718bb8a8
```

```
globus-connect-server collection update 3eccaccf-e99d-41a4-b115-4082718bb8a8 --enable-https --force-encryption --allow-guest-collections --private
```

## Setup JupyterHub

- `t3.medium`
- Instance `i-0d832880d09343e62`
-  Elastic IP `100.23.0.121`
- `172.31.21.55`
- update, upgrade, reboot

### Route 53

A record

```
(base) rpwagner@Mac ~ % nslookup jupyterhub.rickwagner.io
Server:		2600:1700:b840:e70::1
Address:	2600:1700:b840:e70::1#53

Non-authoritative answer:
Name:	jupyterhub.rickwagner.io
Address: 100.23.0.121
```


## Needs

- Globus subscription for managed endpoint


- add student Group information to [login page template](templates/login.html) 
- put template somewhere

https://jupyterhub.readthedocs.io/en/latest/api/app.html?#jupyterhub.app.JupyterHub.template_vars


```
template_vars c.JupyterHub.template_vars = Dict()
Extra variables to be passed into jinja templates
```
- `workshopname`
- `studentgroup`


- override, make Markdown preview default

- update Welcome.md

- put your data in place

- set permissions on your collection

## Costs

### EFS 

- Storage `$0.16/month`
- Elastic Throughput - Reads `$0.03/GB`
- Elastic Throughput - Writes `$0.06/GB`
- `10GB = $1.60/month` + `$0.30/full read` + `$0.60/full write`

### EC2

- `t3.medium $0.0416 2 vCPU 4 GiB RAM EBS Only Up to 5 Gigabit`
- `2@t3.medium = 2 x $0.9984/day = $1.9968/day = $59.90/month`
- EBS `gp3 = $0.08/GB/month`
- `2@32GB = 64 x $0.08/month = $5.12/month`
- Elastic IPs `$0.005/hour`
- `2 @ Elastic IP = $0.24/day = $7.20/month`

