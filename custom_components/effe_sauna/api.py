"""Client for the Effe "My Effe" cloud (ECC V4 modules).

The ECC V4 module has no usable local API: its only open port (81) is an
authenticated WebSocket the official app never talks to. Everything here
mirrors what the My Effe app does against the Effe cloud:

* login       AWS Cognito (user pool client of the app)
* REST        https://api.my.effe.it/v1/ecc[...], bearer = Cognito access token
* push        AWS AppSync GraphQL subscription ``eccUpdate``
"""
from __future__ import annotations

import asyncio
import base64
from collections import deque
from collections.abc import Callable
import json
import logging
import time
from typing import Any
import uuid

import aiohttp

from .const import (
    API_BASE,
    APPSYNC_HOST,
    APPSYNC_REALTIME_HOST,
    COGNITO_CLIENT_ID,
    COGNITO_URL,
    COMMAND_VERSION,
    DIAGNOSTIC_MESSAGE_COUNT,
)

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=20)
TOKEN_REFRESH_MARGIN = 300  # seconds before expiry
PUSH_RECONNECT_MIN = 5
PUSH_RECONNECT_MAX = 300

# Field selection copied from the app; AppSync rejects fields it does not know.
SUBSCRIPTION = """subscription EccStatusUpdateSubscription {
  eccUpdate(eccId: "%s") {
    eccId firmwareVersion hostId systemType temperatureMeasureUnit lastSeenAt
    alarm {
      generic { deviceNotFound masterNotFound timestamp }
      hammam { boilerFullTooSoon cabTemp capacitive door evDrain evLoad fan heaterFail ntc slave timestamp vinBus }
      sauna { stoveTemp vinBus ntc thermalProtection cabTemp potentiometer timestamp }
    }
    functionalities { hammamAuxHeater hammamLight hammamMood hammamRgb mapLight mapMood mapRain mapRgb mapShowerHead mapWaterfall saunaAuxHeater saunaIr saunaLight saunaMood saunaRgb }
    readOnlyState { bsDrying bsLowH2O hRemoteContact hRemoteCnfg hReady hMoodEn hFountEn hFlush hDoor hChromoEn eccOn bsRHSensor hWaterHardness hWashTime hWarmReady hWarmEn hTimer hService hRemoteOn timestamp sTimer sRemoteOn sRemoteContact sRemoteCnfg sReady sDoor sCabTempOffset sCabRHOffset }
    state {
      hammam { chromoOn auxHeaterOn chromoShow lightOn moodOn panelOn pauseOn setpointHammam setpointAuxHeater setpointWarm steamOn timestamp warmOn }
      sauna { panelOn saunaOn biosaunaOn lightOn chromoOn chromoShow moodOn irOn setpointSauna setpointRelativeHumidity timestamp }
    }
    network { ssid bssid ipv4 netif signal }
  }
}"""


class EffeError(Exception):
    """Base error."""


class EffeAuthError(EffeError):
    """Credentials rejected."""


class EffeConnectionError(EffeError):
    """Cloud not reachable or unexpected answer."""


class EffeClient:
    """Authenticated access to the Effe cloud."""

    def __init__(self, session: aiohttp.ClientSession, email: str, password: str) -> None:
        self._session = session
        # Cognito user names are the lower-cased e-mail address.
        self._email = email.strip().lower()
        self._password = password
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._expires_at = 0.0
        self._auth_lock = asyncio.Lock()
        self.messages: deque[dict[str, Any]] = deque(maxlen=DIAGNOSTIC_MESSAGE_COUNT)

    def record(self, direction: str, kind: str, data: Any) -> None:
        """Keep raw traffic for diagnostics."""
        self.messages.append(
            {"time": time.time(), "direction": direction, "kind": kind, "data": data}
        )

    # --- authentication -------------------------------------------------

    async def _cognito(self, flow: str, params: dict[str, str]) -> dict[str, Any]:
        try:
            async with self._session.post(
                COGNITO_URL,
                data=json.dumps(
                    {"AuthFlow": flow, "ClientId": COGNITO_CLIENT_ID, "AuthParameters": params}
                ),
                headers={
                    "Content-Type": "application/x-amz-json-1.1",
                    "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
                },
                timeout=REQUEST_TIMEOUT,
            ) as resp:
                body = await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise EffeConnectionError(f"Login request failed: {err}") from err
        if "AuthenticationResult" not in body:
            kind = body.get("__type", "")
            if kind in ("NotAuthorizedException", "UserNotFoundException"):
                raise EffeAuthError(body.get("message", kind))
            raise EffeConnectionError(f"Login failed: {kind or body}")
        return body["AuthenticationResult"]

    async def async_login(self) -> None:
        """Log in with e-mail and password."""
        result = await self._cognito(
            "USER_PASSWORD_AUTH", {"USERNAME": self._email, "PASSWORD": self._password}
        )
        self._store_tokens(result)

    def _store_tokens(self, result: dict[str, Any]) -> None:
        self._access_token = result["AccessToken"]
        self._refresh_token = result.get("RefreshToken", self._refresh_token)
        self._expires_at = time.monotonic() + result.get("ExpiresIn", 3600)

    async def async_token(self, force: bool = False) -> str:
        """Return a valid access token, refreshing or re-logging in as needed."""
        async with self._auth_lock:
            if (
                not force
                and self._access_token
                and time.monotonic() < self._expires_at - TOKEN_REFRESH_MARGIN
            ):
                return self._access_token
            if self._refresh_token:
                try:
                    self._store_tokens(
                        await self._cognito(
                            "REFRESH_TOKEN_AUTH", {"REFRESH_TOKEN": self._refresh_token}
                        )
                    )
                    return self._access_token
                except EffeAuthError:
                    self._refresh_token = None
            await self.async_login()
            return self._access_token

    # --- REST -----------------------------------------------------------

    async def _request(self, method: str, path: str, payload: dict | None = None) -> Any:
        for attempt in (0, 1):
            token = await self.async_token(force=attempt == 1)
            try:
                async with self._session.request(
                    method,
                    f"{API_BASE}/{path}",
                    json=payload,
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=REQUEST_TIMEOUT,
                ) as resp:
                    if resp.status == 401 and attempt == 0:
                        continue
                    if resp.status in (401, 403):
                        raise EffeAuthError(f"{method} {path}: HTTP {resp.status}")
                    if resp.status >= 400:
                        raise EffeConnectionError(
                            f"{method} {path}: HTTP {resp.status} {(await resp.text())[:200]}"
                        )
                    data = await resp.json(content_type=None)
            except (aiohttp.ClientError, TimeoutError, ValueError) as err:
                raise EffeConnectionError(f"{method} {path}: {err}") from err
            self.record("rx", f"{method} {path}", data)
            return data
        raise EffeAuthError(f"{method} {path}: not authorized")

    async def async_get_me(self) -> dict[str, Any]:
        """Return the account record."""
        return await self._request("GET", "me")

    async def async_get_devices(self) -> list[dict[str, Any]]:
        """Return all ECC modules paired with the account, including state."""
        return (await self._request("GET", "ecc")).get("data", [])

    async def async_send_command(
        self, device: dict[str, Any], function: str, target: str, value: str
    ) -> None:
        """Send one command in the app's format."""
        payload = {
            "eccId": device["eccId"],
            "hostId": device.get("hostId"),
            "function": function,
            "target": target,
            "value": value,
            "version": COMMAND_VERSION,
        }
        self.record("tx", "command", payload)
        await self._request("POST", f"ecc/{device['eccId']}/command", payload)

    # --- push -----------------------------------------------------------

    async def async_listen(
        self,
        ecc_ids: list[str],
        on_update: Callable[[dict[str, Any]], None],
        on_connection: Callable[[bool], None],
    ) -> None:
        """Hold the AppSync subscription open forever, reconnecting as needed."""
        delay = PUSH_RECONNECT_MIN
        while True:
            started = time.monotonic()
            try:
                await self._listen_once(ecc_ids, on_update, on_connection)
            except asyncio.CancelledError:
                on_connection(False)
                raise
            except (EffeError, aiohttp.ClientError, TimeoutError, ValueError) as err:
                _LOGGER.debug("Push connection lost: %s", err)
                self.record("rx", "push_error", str(err))
            on_connection(False)
            if time.monotonic() - started > 60:
                delay = PUSH_RECONNECT_MIN
            await asyncio.sleep(delay)
            delay = min(delay * 2, PUSH_RECONNECT_MAX)

    async def _listen_once(
        self,
        ecc_ids: list[str],
        on_update: Callable[[dict[str, Any]], None],
        on_connection: Callable[[bool], None],
    ) -> None:
        token = await self.async_token()
        token_expires = self._expires_at
        auth = {"host": APPSYNC_HOST, "Authorization": token}
        header = base64.b64encode(json.dumps(auth).encode()).decode()
        url = f"wss://{APPSYNC_REALTIME_HOST}/graphql?header={header}&payload=e30="
        async with self._session.ws_connect(
            url, protocols=("graphql-ws",), heartbeat=None, timeout=20
        ) as ws:
            await ws.send_json({"type": "connection_init"})
            keepalive = 300.0
            pending = set()
            while True:
                # Reconnect with a fresh token before the current one expires.
                remaining = token_expires - TOKEN_REFRESH_MARGIN - time.monotonic()
                if remaining <= 0:
                    return
                msg = await ws.receive(timeout=min(keepalive + 15, remaining))
                if msg.type in (
                    aiohttp.WSMsgType.CLOSE,
                    aiohttp.WSMsgType.CLOSED,
                    aiohttp.WSMsgType.CLOSING,
                    aiohttp.WSMsgType.ERROR,
                ):
                    raise EffeConnectionError(f"Push socket closed ({msg.type.name})")
                if msg.type is not aiohttp.WSMsgType.TEXT:
                    continue
                data = json.loads(msg.data)
                kind = data.get("type")
                if kind == "ka":
                    continue
                self.record("rx", f"push_{kind}", data.get("payload"))
                if kind == "connection_ack":
                    keepalive = (
                        data.get("payload", {}).get("connectionTimeoutMs", 300000) / 1000
                    )
                    for ecc_id in ecc_ids:
                        sub_id = str(uuid.uuid4())
                        pending.add(sub_id)
                        await ws.send_json(
                            {
                                "id": sub_id,
                                "type": "start",
                                "payload": {
                                    "data": json.dumps(
                                        {"query": SUBSCRIPTION % ecc_id, "variables": {}}
                                    ),
                                    "extensions": {"authorization": auth},
                                },
                            }
                        )
                elif kind == "start_ack":
                    pending.discard(data.get("id"))
                    if not pending:
                        on_connection(True)
                elif kind == "data":
                    update = (data.get("payload", {}).get("data") or {}).get("eccUpdate")
                    if update:
                        on_update(update)
                elif kind in ("error", "connection_error"):
                    raise EffeConnectionError(f"Push error: {data.get('payload')}")
