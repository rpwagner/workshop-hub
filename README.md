# workshop-hub

Data-Enabled JupyterHub Example

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
