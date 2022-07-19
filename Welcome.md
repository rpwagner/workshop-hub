# Welcome to a Data-Enabled Workshop

Refer to this page to find helpful links to each interactive notebook. Remember that you will need to make a copy of these notebooks into your own space before running/trying to modify!

The example links are in code blocks. Once you have your collection
UUID or hostname in them, remove the backticks ``` to make them links
in the document.

## Example Links

### Slides

```
- [Onboarding](https://{your-collection-hostname}.data.globus.org/public-data/programming/slides/WorkshopWelcome.pdf)
```

### Notebooks

```
- [Programming](public-data/programming/IntroToProgramming.ipynb)
```

## About this Jupyterhub

### Data

User data is accessible within the notebook environment and via
Globus. Data from public-data and shared-data can be downloaded/transferred using 
Jupyter's built-in interface, or via this 

```
[Globus link](https://app.globus.org/file-manager?origin_id={your-collection-UUID}) 
```

### Notebook Environment

This is the environment within the running Docker container that hosts
the user's Jupyter notebooks. The home directory, `/home/jovyan`, can
be written to, but is not persistent.

`/home/jovyan/work/` is the default directory for the notebook server
and what the root in the JupyterLab file manager. There is also the
line `cd ~/work` in the Bash configuration so that when a terminal is
opened the user goes straight there. This folder is bind mounted from
the user's folder in the Globus collection.

The `/public-data/` folder from the Globus collection is bind
mounted read-only at `/home/jovyan/work/public-data/`.

The `/shared-data/` folder from the Globus collection is bind
mounted read-write at `/home/jovyan/work/shared-data/`.

| Folder or File     | Permissions | Persistent | Globus |
| ----------- | ----------- | ------ | ----- |
| `/home/jovyan` | RW | No | No |
| `/home/jovyan/work` | RW | Yes | Yes, at `/{username}/` |
| `/home/jovyan/work/Welcome.md` | RO | Yes | No |
| `/home/jovyan/work/public-data` | RO | Yes | Yes, at `[/public-data/](https://app.globus.org/file-manager?origin_id={your-collection-uuid}&origin_path=%2Fpublic-data%2F)` |
| `/home/jovyan/work/shared-data` | RW | Yes | Yes, at `[/shared-data/](https://app.globus.org/file-manager?origin_id={your-collection-uuid}&origin_path=%2Fshared-data%2F)` |
