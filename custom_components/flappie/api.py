"""Async Python client for the undocumented Flappie cloud API.

Port of the npm package ``flappie-api`` (https://github.com/ooswald/flappie-api).
The vendor has not published an official API; endpoints can change at any time.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import BASE_URL

_LOGGER = logging.getLogger(__name__)

_TIMEOUT = aiohttp.ClientTimeout(total=30)


class FlappieApiError(Exception):
    """Generic Flappie API error."""

    def __init__(
        self, message: str, status: int | None = None, body: Any = None
    ) -> None:
        super().__init__(message)
        self.status = status
        self.body = body


class FlappieAuthError(FlappieApiError):
    """Raised when credentials are rejected."""


class FlappieApiClient:
    """Minimal async client for app.flappiedoors.com."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        email: str,
        password: str,
        base_url: str = BASE_URL,
    ) -> None:
        self._session = session
        self._email = email
        self._password = password
        self._base_url = base_url.rstrip("/")
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._auth_lock = asyncio.Lock()

    # ---------------------------------------------------------------- auth

    async def async_login(self) -> None:
        """Exchange credentials for a token pair."""
        async with self._session.post(
            f"{self._base_url}/api/v1/users/login",
            json={"email": self._email, "password": self._password},
            timeout=_TIMEOUT,
        ) as resp:
            body = await _read_body(resp)
            if resp.status in (400, 401, 403, 422):
                raise FlappieAuthError(
                    f"Login failed with status {resp.status}", resp.status, body
                )
            if resp.status >= 400:
                raise FlappieApiError(
                    f"Login failed with status {resp.status}", resp.status, body
                )
        self._access_token = body["access_token"]
        self._refresh_token = body.get("refresh_token")

    async def _async_refresh(self) -> bool:
        """Refresh the access token; return True on success."""
        if not self._refresh_token:
            return False
        try:
            async with self._session.post(
                f"{self._base_url}/api/v1/users/refresh",
                headers={"refresh-token": self._refresh_token},
                timeout=_TIMEOUT,
            ) as resp:
                if resp.status >= 400:
                    return False
                body = await _read_body(resp)
        except (aiohttp.ClientError, TimeoutError):
            return False
        self._access_token = body["access_token"]
        self._refresh_token = body.get("refresh_token", self._refresh_token)
        return True

    async def _async_reauth(self) -> None:
        """Refresh the token pair, falling back to a fresh login."""
        async with self._auth_lock:
            if await self._async_refresh():
                return
            await self.async_login()

    # ------------------------------------------------------------- request

    async def _async_request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict[str, str] | None = None,
        _retry: bool = True,
    ) -> Any:
        if self._access_token is None:
            await self._async_reauth()

        try:
            async with self._session.request(
                method,
                f"{self._base_url}{path}",
                json=json,
                params=params,
                headers={"Authorization": f"Bearer {self._access_token}"},
                timeout=_TIMEOUT,
            ) as resp:
                if resp.status == 401 and _retry:
                    await self._async_reauth()
                    return await self._async_request(
                        method, path, json=json, params=params, _retry=False
                    )
                body = await _read_body(resp)
                if resp.status == 401:
                    raise FlappieAuthError(
                        f"{method} {path} -> 401", resp.status, body
                    )
                if resp.status >= 400:
                    raise FlappieApiError(
                        f"{method} {path} -> {resp.status}: {body}",
                        resp.status,
                        body,
                    )
                return body
        except (aiohttp.ClientError, TimeoutError) as err:
            raise FlappieApiError(f"{method} {path} failed: {err}") from err

    # ------------------------------------------------------------ endpoints

    async def async_get_user(self) -> dict[str, Any]:
        return await self._async_request("GET", "/api/v1/users")

    async def async_get_devices(self) -> list[dict[str, Any]]:
        return await self._async_request("GET", "/api/v1/devices")

    async def async_get_device_information(self, device_id: str) -> dict[str, Any]:
        return await self._async_request(
            "GET", f"/api/v1/devices/{device_id}/information"
        )

    async def async_get_device_status(self, device_id: str) -> dict[str, Any]:
        return await self._async_request("GET", f"/api/v1/devices/{device_id}/status")

    async def async_get_device_settings(self, device_id: str) -> dict[str, Any]:
        # Achtung: das Backend erwartet hier KEINEN Slash vor der Device-ID.
        return await self._async_request("GET", f"/api/v1/devices{device_id}/settings")

    async def async_patch_device_settings(
        self, device_id: str, patch: dict[str, Any]
    ) -> dict[str, Any]:
        # Gleicher Slash-Quirk wie beim GET; Antwort ist das volle Settings-Objekt.
        return await self._async_request(
            "PATCH", f"/api/v1/devices{device_id}/settings", json=patch
        )

    async def async_list_cats(self) -> list[dict[str, Any]]:
        return await self._async_request("GET", "/api/v1/cats")

    async def async_get_dashboard(self) -> dict[str, Any]:
        return await self._async_request("GET", "/api/v1/dashboard")

    async def async_list_bundles(
        self,
        *,
        page: int = 1,
        only_prey: bool | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, str] = {
            "page": str(page),
            "order_by": "createdAt",
            "sort_order": "desc",
        }
        if only_prey is not None:
            params["only_prey"] = "true" if only_prey else "false"
        if from_date is not None:
            params["fromCreatedAt"] = from_date
        if to_date is not None:
            params["toCreatedAt"] = to_date
        return await self._async_request("GET", "/api/v1/bundles", params=params)

    async def async_get_prey_stats(
        self,
        *,
        group_by: str = "day",
        start_date: str,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        params = {"group_by_period": group_by, "start_date": start_date}
        if end_date is not None:
            params["end_date"] = end_date
        return await self._async_request(
            "GET", "/api/v1/statistics/prey", params=params
        )

    async def async_get_bundle(self, bundle_id: int) -> dict[str, Any]:
        """Fetch one bundle; returns fresh (signed, kurzlebige) Medien-URLs."""
        return await self._async_request("GET", f"/api/v1/bundles/{bundle_id}")


async def _read_body(resp: aiohttp.ClientResponse) -> Any:
    try:
        return await resp.json(content_type=None)
    except ValueError:
        return await resp.text()
