from typing import Any, Dict, Optional


class Route:
    def __init__(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ):
        self.method = method
        self.endpoint = endpoint
        self.params = params if params else {}
        self.data = data if data else {}
        self.json = json if json else {}
