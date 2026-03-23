# -*- coding: utf-8 -*-
"""DingTalk Enterprise OIDC token validator with Discovery support."""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from app.atlasclaw.auth.providers.base import AuthProvider
from app.atlasclaw.auth.providers.oidc import OIDCProvider
from app.atlasclaw.auth.models import AuthResult, AuthenticationError

logger = logging.getLogger(__name__)


class DingTalkOIDCProvider(OIDCProvider):
    """
    DingTalk Enterprise OIDC token validator.

    Extends the standard OIDCProvider with:
      - OIDC Discovery: auto-resolves JWKS URI from .well-known/openid-configuration
      - DingTalk-specific claim mappings: corpId -> tenant_id, sub_mapping hint
      - AuthRegistry auto-discovery via auth_id class attribute
    """

    # Required for AuthRegistry auto-discovery by ProviderScanner
    auth_id = "dingtalk_oidc"
    auth_name = "DingTalk OIDC"

    def __init__(
        self,
        issuer: str,
        client_id: str,
        jwks_uri: str = "",
        discovery_url: str = "",
        corp_id: str = "",
        sub_mapping: str = "userid",
    ) -> None:
        super().__init__(issuer=issuer, client_id=client_id, jwks_uri=jwks_uri)
        self._discovery_url = (
            discovery_url
            or f"{issuer.rstrip('/')}/.well-known/openid-configuration"
        )
        self._corp_id = corp_id
        self._sub_mapping = sub_mapping
        self._discovery_cache: Optional[dict[str, Any]] = None

    def provider_name(self) -> str:
        return "dingtalk_oidc"

    async def _discover_endpoints(self) -> dict[str, Any]:
        """Fetch and cache the OIDC Discovery document."""
        if self._discovery_cache is not None:
            return self._discovery_cache
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(self._discovery_url)
                resp.raise_for_status()
                self._discovery_cache = resp.json()
        except Exception as exc:
            raise AuthenticationError(
                f"Failed to fetch OIDC Discovery from {self._discovery_url}: {exc}"
            ) from exc
        return self._discovery_cache

    async def _fetch_jwks(self) -> dict[str, Any]:
        """Override: resolve jwks_uri via Discovery if not explicitly set."""
        if not self._jwks_uri or "/.well-known/" in self._jwks_uri:
            discovery = await self._discover_endpoints()
            resolved = discovery.get("jwks_uri", "")
            if resolved:
                self._jwks_uri = resolved
                logger.info(
                    "[DingTalk OIDC] Resolved jwks_uri via Discovery: %s",
                    self._jwks_uri,
                )
        return await super()._fetch_jwks()

    async def authenticate(self, credential: str) -> AuthResult:
        """Override: enrich AuthResult with DingTalk-specific mappings."""
        result = await super().authenticate(credential)

        # Map corpId -> tenant_id
        if self._corp_id:
            result.tenant_id = self._corp_id
        elif result.extra.get("corp_id"):
            result.tenant_id = result.extra["corp_id"]

        # Store sub_mapping hint for downstream consumers
        result.extra["dingtalk_sub_mapping"] = self._sub_mapping

        return result
