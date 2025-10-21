export class TTSR {
  constructor(baseUrl, clientId, clientSecret) {
    this.base = baseUrl.replace(/\/$/, "");
    this.clientId = clientId;
    this.clientSecret = clientSecret;
    this._token = null;
  }
  async _getToken(scope = "score:write events:read") {
    if (this._token) return this._token;
    const res = await fetch(`${this.base}/v1/oauth2/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        grant_type: "client_credentials",
        client_id: this.clientId,
        client_secret: this.clientSecret,
        scope
      })
    });
    if (!res.ok) throw new Error(`Token failed ${res.status}`);
    const json = await res.json();
    this._token = json.access_token;
    return this._token;
  }
  async score(payload, idempotencyKey) {
    const tok = await this._getToken("score:write");
    const res = await fetch(`${this.base}/v1/score`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${tok}`,
        "Content-Type": "application/json",
        "Idempotency-Key": idempotencyKey
      },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error(`Score failed ${res.status}`);
    return { json: await res.json(), headers: res.headers };
  }
  async getEvent(eventId) {
    const tok = await this._getToken("events:read");
    const res = await fetch(`${this.base}/v1/events/${eventId}`, {
      headers: { "Authorization": `Bearer ${tok}` }
    });
    if (!res.ok) throw new Error(`Get event failed ${res.status}`);
    return { json: await res.json(), headers: res.headers };
  }
}
