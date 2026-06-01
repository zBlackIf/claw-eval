"""Feishu Bot - Message sender module."""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class FeishuMessageSender:
    """Sends messages to Feishu users via Open API."""

    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self._token: str | None = None

    def _get_tenant_token(self) -> str:
        """Get tenant access token from Feishu."""
        if self._token:
            return self._token
        resp = httpx.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret},
        )
        data = resp.json()
        self._token = data.get("tenant_access_token", "")
        return self._token

    def send_text(self, user_id: str, text: str) -> dict[str, Any]:
        """Send a text message to a user."""
        token = self._get_tenant_token()
        resp = httpx.post(
            "https://open.feishu.cn/open-apis/im/v1/messages",
            params={"receive_id_type": "open_id"},
            headers={"Authorization": f"Bearer {token}"},
            json={
                "receive_id": user_id,
                "msg_type": "text",
                "content": f'{{"text": "{text}"}}',
            },
        )
        return resp.json()

    def send_rich_text(self, user_id: str, title: str, content_blocks: list) -> dict[str, Any]:
        """Send a rich text (post) message to a user."""
        token = self._get_tenant_token()
        import json
        post_content = json.dumps({
            "zh_cn": {
                "title": title,
                "content": content_blocks,
            }
        })
        resp = httpx.post(
            "https://open.feishu.cn/open-apis/im/v1/messages",
            params={"receive_id_type": "open_id"},
            headers={"Authorization": f"Bearer {token}"},
            json={
                "receive_id": user_id,
                "msg_type": "post",
                "content": post_content,
            },
        )
        return resp.json()
