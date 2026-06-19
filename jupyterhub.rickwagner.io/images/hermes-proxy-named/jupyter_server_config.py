import os

HERMES_API_KEY = os.environ['HERMES_API_KEY'].strip()

c.ServerProxy.servers = {
    "agent": {
        "command": ["start-hermes-gateway", "{port}"],
        "timeout": 90,
        "absolute_url": False,
        "request_headers_override": {
            "Authorization": f"Bearer {HERMES_API_KEY}"
        },
        "launcher_entry": {
            "title": "Hermes API",
            "path_info": "hermes/health",
            "category": "Other",
        },
        "new_browser_tab": True,
    }
}
