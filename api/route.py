from typing import Any, Dict, Optional
from urllib.parse import urlencode

class Route:
    def __init__(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):

        if "#" in endpoint:
            endpoint = endpoint.replace("#", "%23")

        if kwargs:
            url_params = {}
            for k, v in kwargs.items():
                if v is None:
                    continue
                url_params[k] = v
            self.endpoint = "{}?{}".format(endpoint, urlencode(url_params))
        else:
            self.endpoint = endpoint

        self.method = method
        self.data = data
        self.json = json
