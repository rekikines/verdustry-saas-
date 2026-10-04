import requests


class RESTConnector:
    """Connecteur generique en lecture seule pour API REST externes."""

    def __init__(self, base_url: str, auth_type: str, credentials: dict, default_headers: dict | None = None):
        self.base_url = base_url.rstrip("/")
        self.auth_type = auth_type
        self.credentials = credentials or {}
        self.default_headers = default_headers or {}

    def _build_headers(self) -> dict:
        headers = dict(self.default_headers)
        if self.auth_type == "bearer":
            headers["Authorization"] = f"Bearer {self.credentials.get('token', '')}"
        elif self.auth_type == "api_key":
            header_name = self.credentials.get("header_name", "X-API-Key")
            headers[header_name] = self.credentials.get("api_key", "")
        return headers

    def _build_auth(self):
        if self.auth_type == "basic":
            return (self.credentials.get("username", ""), self.credentials.get("password", ""))
        return None

    def test_connection(self, endpoint_path: str, method: str = "GET", params: dict | None = None) -> bool:
        try:
            resp = requests.request(
                method, f"{self.base_url}/{endpoint_path.lstrip('/')}",
                headers=self._build_headers(), auth=self._build_auth(),
                params=params if method == "GET" else None,
                json=params if method == "POST" else None,
                timeout=10,
            )
            return resp.status_code < 400
        except requests.RequestException as e:
            raise ConnectionError(f"Echec de connexion API : {e}")

    def fetch_page(self, endpoint_path: str, method: str = "GET", query_params: dict | None = None, body: dict | None = None) -> dict:
        try:
            resp = requests.request(
                method, f"{self.base_url}/{endpoint_path.lstrip('/')}",
                headers=self._build_headers(), auth=self._build_auth(),
                params=query_params if method == "GET" else None,
                json=body if method == "POST" else None,
                timeout=20,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            raise RuntimeError(f"Erreur d'extraction API : {e}")