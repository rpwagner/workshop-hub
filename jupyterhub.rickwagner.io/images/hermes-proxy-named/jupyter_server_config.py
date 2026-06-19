import os

hermes_port = int(os.environ.get("API_SERVER_PORT", "8642"))
hermes_key = os.environ['HERMES_API_KEY'].strip()

c.ServerProxy.servers = {
    "hermes": {
        # Hermes is started by scripts/20-start-hermes-gateway.sh.
        # An empty command tells jupyter-server-proxy to proxy an already-running service.
        "command": [],
        "port": hermes_port,
        "absolute_url": False,
        "timeout": 30,
        "request_headers_override": {
            "Authorization": f"Bearer {hermes_key}",
        },
        "launcher_entry": {
            "enabled": True,
            "title": "Hermes API",
            "path_info": "health",
            "category": "Other",
            "new_browser_tab": True
        },
        "new_browser_tab": True
    }
}
