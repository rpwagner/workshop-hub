lines = open('/home/jovyan/work/.hermes/.env').readlines()
conf = {}
for l in lines:
    key, val = l.split('=')
    conf[key] = val.strip()

c = get_config()

c.ServerProxy.servers = {
    "hermes-api": {
        # Hermes is started by scripts/20-start-hermes-gateway.sh.
        # An empty command tells jupyter-server-proxy to proxy an already-running service.
        "command": ["hermes", "gateway"],
        "port": int(conf['API_SERVER_PORT']),
        "absolute_url": False,
        "timeout": 30,
        "request_headers_override": {
            "Authorization": f"Bearer {conf['API_SERVER_KEY']}",
        },
        "launcher_entry": {
            "enabled": True,
            "title": "Hermes API",
            "path_info": "hermes-api/health",
            "category": "Agents",
            "new_browser_tab": True
        },
        "new_browser_tab": True
    },
    "hermes-dashboard": {
        # Hermes is started by scripts/20-start-hermes-gateway.sh.
        # An empty command tells jupyter-server-proxy to proxy an already-running service.
        "command": ["hermes", "dashboard"],
        "port": int(conf['API_SERVER_PORT']),
        "absolute_url": False,
        "timeout": 30,
        "request_headers_override": {
            "Authorization": f"Bearer {conf['API_SERVER_KEY']}",
        },
        "launcher_entry": {
            "enabled": True,
            "title": "Hermes Dashboard",
#            "path_info": "hermes-api/health",
            "category": "Agents",
            "new_browser_tab": True
        },
        "new_browser_tab": True
    }
}
