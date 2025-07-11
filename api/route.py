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

        # (optional) percent-encode any stray # in the path
        if '#' in endpoint:
            endpoint = endpoint.replace('#', '%23')

        # build only the params that aren't None
        params = {k: v for k, v in kwargs.items() if v is not None}

        if params:
            # doseq=True makes lists repeat the key
            qs = urlencode(params, doseq=True)
            self.endpoint = f'{endpoint}?{qs}'
        else:
            self.endpoint = endpoint

        self.method = method
        self.data = data
        self.json = json
