import requests

class TTSR:
    def __init__(self, base_url: str, client_id: str, client_secret: str):
        self.base = base_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self._token = None

    def _get_token(self, scope="score:write events:read"):
        if self._token:  # naive cache
            return self._token
        r = requests.post(f"{self.base}/v1/oauth2/token",
                          headers={"Content-Type":"application/x-www-form-urlencoded"},
                          data={"grant_type":"client_credentials","client_id":self.client_id,"client_secret":self.client_secret,"scope":scope})
        r.raise_for_status()
        self._token = r.json()["access_token"]
        return self._token

    def score(self, payload: dict, idempotency_key: str):
        tok = self._get_token("score:write")
        r = requests.post(f"{self.base}/v1/score",
                          headers={"Authorization":f"Bearer {tok}","Content-Type":"application/json","Idempotency-Key":idempotency_key},
                          json=payload)
        r.raise_for_status()
        return r.json(), r.headers

    def get_event(self, event_id: str):
        tok = self._get_token("events:read")
        r = requests.get(f"{self.base}/v1/events/{event_id}",
                         headers={"Authorization":f"Bearer {tok}"})
        r.raise_for_status()
        return r.json(), r.headers
