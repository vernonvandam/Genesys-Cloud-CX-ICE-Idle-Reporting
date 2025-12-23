
# gcloud/client.py

import os
import base64
import requests
import PureCloudPlatformClientV2 as p
from PureCloudPlatformClientV2.rest import ApiException
from utils import console

# ------------------------------------------------------------------------------
# SDK logger settings (keep terse for production)
# ------------------------------------------------------------------------------
p.configuration.logger.log_level = p.logger.LogLevel.LError
p.configuration.logger.log_request_body = True
p.configuration.logger.log_response_body = True
p.configuration.logger.log_format = p.logger.LogFormat.TEXT
p.configuration.logger.log_to_console = True
# p.configuration.logger.log_file_path = "/var/log/pythonsdk.log"

# Global API client instance
gApiClient = None


def _clean(value: str) -> str:
    """Strip whitespace and accidental wrapping quotes."""
    if value is None:
        return ""
    v = value.strip()
    if len(v) >= 2 and ((v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'"))):
        v = v[1:-1].strip()
    return v


def _derive_login_host_from_api_host(api_host: str) -> str:
    """
    Derive the region login host from the API host by swapping 'api.' for 'login.' on the same domain.
    If derivation fails, fallback to AU login (Sydney).
    """
    api_host = _clean(api_host).lower()
    if api_host.startswith("https://api."):
        return "https://login." + api_host[len("https://api."):]
    # Fallback for Sydney if API_HOST isn't set properly
    return "https://login.mypurecloud.com.au"


def _get_token_via_login_host(login_host: str, client_id: str, client_secret: str) -> str:
    """
    Obtain an OAuth token using Client Credentials against the region login host,
    mirroring the documented flow:
      POST {login_host}/oauth/token
      Authorization: Basic base64(<client_id>:<client_secret>)
      grant_type=client_credentials
    """
    login_host = _clean(login_host).rstrip("/")
    url = f"{login_host}/oauth/token"

    cid = _clean(client_id)
    csec = _clean(client_secret)
    if not cid or not csec:
        raise RuntimeError("Missing OAuth client credentials")

    # Basic authorization header identical to cURL
    basic_b64 = base64.b64encode(f"{cid}:{csec}".encode("utf-8")).decode("ascii")
    headers = {
        "Authorization": f"Basic {basic_b64}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"grant_type": "client_credentials"}

    resp = requests.post(url, headers=headers, data=data, timeout=15)
    if resp.status_code >= 400:
        corr = resp.headers.get("Inin-Correlation-Id", "(none)")
        body_preview = resp.text[:200]
        raise requests.HTTPError(
            f"{resp.status_code} invalid_client at {url} (corrId={corr}): {body_preview}",
            response=resp,
        )

    payload = resp.json()
    token = payload.get("access_token")
    if not token:
        raise RuntimeError(f"Token response missing access_token: {payload}")
    return token


def initApiClient():
    """
    Initialise the Genesys Cloud SDK by reading configuration from environment variables:

      Required:
        - API_HOST (e.g., https://api.mypurecloud.com.au)
        - GENESYS_CLOUD_CLIENT_ID
        - GENESYS_CLOUD_CLIENT_SECRET

      Optional:
        - GENESYS_CLOUD_LOGIN_HOST (if omitted, derived from API_HOST)
        - GENESYS_CLOUD_REGION (used only if API_HOST is absent; maps ap_southeast_2 → AU)

    Steps:
      1) Validate & sanitize env values.
      2) Set SDK base host for the region.
      3) Obtain token from the region login host via client-credentials.
      4) Inject token into SDK and return ApiClient.
    """
    global gApiClient

    # Read from environment (sanitized)
    api_host      = _clean(os.getenv("API_HOST"))
    client_id     = _clean(os.getenv("GENESYS_CLOUD_CLIENT_ID"))
    client_secret = _clean(os.getenv("GENESYS_CLOUD_CLIENT_SECRET"))
    login_host    = _clean(os.getenv("GENESYS_CLOUD_LOGIN_HOST"))

    # If API_HOST is missing, fallback via region (minimal mapping for Sydney)
    if not api_host:
        region = _clean(os.getenv("GENESYS_CLOUD_REGION"))
        if region == "ap_southeast_2":
            api_host = "https://api.mypurecloud.com.au"
        else:
            raise RuntimeError(
                "API_HOST is missing and GENESYS_CLOUD_REGION is not mapped. "
                "Set API_HOST explicitly in .env."
            )

    if not client_id or not client_secret:
        console.fail("GENESYS_CLOUD_CLIENT_ID/SECRET are missing or empty.")
        raise RuntimeError("Missing OAuth client credentials")

    # Derive login host if not explicitly set
    login_host = login_host or _derive_login_host_from_api_host(api_host)

    # Set SDK base API host (must match org region)
    p.configuration.host = api_host
    print(f"Host is {p.configuration.host}")

    # Obtain token via documented OAuth client-credentials flow
    token = _get_token_via_login_host(login_host, client_id, client_secret)
    console.ok("Obtained access token from login host.")

    # Inject token and create ApiClient
    p.configuration.access_token = token
    api_client = p.api_client.ApiClient()
    gApiClient = api_client

    console.ok("Genesys Cloud SDK client initialised (token injected).")
    return gApiClient
