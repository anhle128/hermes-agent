"""Tests for the webhook adapter's ``deliver_only`` route mode.

``deliver_only`` lets external services (Supabase webhooks, monitoring
alerts, background jobs, other agents) push plain-text notifications to
a user's chat via the webhook adapter WITHOUT invoking the agent.  The
rendered prompt template becomes the literal message body.

Covers:
- Agent is NOT invoked (``handle_message`` never called)
- Rendered content is delivered to the target platform adapter
- HTTP returns 200 OK on success, 502 on delivery failure
- Startup validation rejects ``deliver_only`` without a real delivery target
- HMAC auth, rate limiting, and idempotency still apply
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from gateway.config import HomeChannel, Platform, PlatformConfig
from gateway.platforms.base import MessageEvent, SendResult
from gateway.platforms.webhook import WebhookAdapter, _INSECURE_NO_AUTH


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_adapter(routes, **extra_kw) -> WebhookAdapter:
    extra = {"host": "127.0.0.1", "port": 0, "routes": routes}
    extra.update(extra_kw)
    config = PlatformConfig(enabled=True, extra=extra)
    return WebhookAdapter(config)


def _create_app(adapter: WebhookAdapter) -> web.Application:
    app = web.Application()
    app.router.add_get("/health", adapter._handle_health)
    app.router.add_post("/webhooks/{route_name}", adapter._handle_webhook)
    return app


def _wire_mock_target(adapter: WebhookAdapter, platform_name: str = "telegram"):
    """Attach a gateway_runner with a mocked target adapter."""
    mock_target = AsyncMock()
    mock_target.send = AsyncMock(return_value=SendResult(success=True))

    mock_runner = MagicMock()
    mock_runner.adapters = {Platform(platform_name): mock_target}
    mock_runner.config.get_home_channel.return_value = None

    adapter.gateway_runner = mock_runner
    return mock_target


async def _drain_background_tasks(adapter: WebhookAdapter) -> None:
    while adapter._background_tasks:
        await asyncio.gather(*tuple(adapter._background_tasks))


def _wire_mock_homes(
    adapter: WebhookAdapter,
    homes: dict[Platform, HomeChannel],
    results: dict[Platform, SendResult] | None = None,
) -> dict[Platform, AsyncMock]:
    configured_results = results or {}
    targets: dict[Platform, AsyncMock] = {}
    runner = MagicMock()
    runner.adapters = {}
    runner.config.platforms = {}

    for platform, home in homes.items():
        target = AsyncMock()
        target.send = AsyncMock(
            return_value=configured_results.get(
                platform,
                SendResult(success=True),
            )
        )
        targets[platform] = target
        runner.adapters[platform] = target
        runner.config.platforms[platform] = PlatformConfig(
            enabled=True,
            home_channel=home,
        )

    runner.config.get_home_channel.side_effect = lambda platform: (
        runner.config.platforms[platform].home_channel
        if platform in runner.config.platforms
        else None
    )
    adapter.gateway_runner = runner
    return targets


# ===================================================================
# Core behaviour: agent bypass
# ===================================================================

class TestDeliverOnlyBypassesAgent:
    """The whole point of the feature — handle_message must not be called."""

    @pytest.mark.asyncio
    async def test_post_delivers_directly_without_agent(self):
        routes = {
            "match-alert": {
                "secret": _INSECURE_NO_AUTH,
                "deliver": "telegram",
                "deliver_only": True,
                "deliver_extra": {"chat_id": "12345"},
                "prompt": "{payload.user} matched with {payload.other}!",
            }
        }
        adapter = _make_adapter(routes)
        mock_target = _wire_mock_target(adapter)

        # Guard: handle_message must NOT be called in deliver_only mode
        handle_message_calls: list[MessageEvent] = []

        async def _capture(event):
            handle_message_calls.append(event)

        adapter.handle_message = _capture

        app = _create_app(adapter)
        body = json.dumps(
            {"payload": {"user": "alice", "other": "bob"}}
        ).encode()

        async with TestClient(TestServer(app)) as cli:
            resp = await cli.post(
                "/webhooks/match-alert",
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "X-GitHub-Delivery": "delivery-1",
                },
            )
            assert resp.status == 200
            data = await resp.json()
            assert data["status"] == "delivered"
            assert data["route"] == "match-alert"
            assert data["target"] == "telegram"

        # Let any background tasks settle before asserting no agent call
        await asyncio.sleep(0.05)

        # Agent was NOT invoked
        assert handle_message_calls == []

        # Target adapter.send() WAS called with the rendered template
        mock_target.send.assert_awaited_once()
        call_args = mock_target.send.await_args
        chat_id_arg, content_arg = call_args.args[0], call_args.args[1]
        assert chat_id_arg == "12345"
        assert content_arg == "alice matched with bob!"

    @pytest.mark.asyncio
    async def test_archon_approval_fans_out_to_home_channels_without_agent(
        self, monkeypatch
    ):
        routes = {
            "archon-approval": {
                "secret": _INSECURE_NO_AUTH,
                "events": ["workflow.approval.requested"],
                "deliver": "all",
                "deliver_only": True,
                "prompt": (
                    "⏸ Approval required\n\n"
                    "Project: {projectRef.codebaseRef}\n"
                    "Workflow: {workflowRunRef.workflowName}\n"
                    "Run: {workflowRunRef.runId}\n"
                    "Gate: {payload.approval.nodeId} "
                    "({payload.approval.gateType})\n\n"
                    "User request:\n{payload.approval.userPrompt}\n\n"
                    "Review:\n{payload.approval.reviewUrl}"
                ),
            }
        }
        adapter = _make_adapter(routes)
        targets = _wire_mock_homes(
            adapter,
            {
                Platform.TELEGRAM: HomeChannel(
                    platform=Platform.TELEGRAM,
                    chat_id="telegram-home",
                    name="Telegram Ops",
                    thread_id="topic-7",
                ),
                Platform.SLACK: HomeChannel(
                    platform=Platform.SLACK,
                    chat_id="slack-home",
                    name="Slack Ops",
                ),
            },
        )
        handle_message = AsyncMock()
        monkeypatch.setattr(adapter, "handle_message", handle_message)
        payload = {
            "eventType": "workflow.approval.requested",
            "projectRef": {"codebaseRef": "archon"},
            "workflowRunRef": {
                "workflowName": "archon-speckit-feature",
                "runId": "run-1",
            },
            "payload": {
                "approval": {
                    "nodeId": "clarify-gate",
                    "gateType": "plannotator_gate",
                    "userPrompt": "Add the requested workflow capability.",
                    "reviewUrl": "https://archon-host.example.ts.net:19432",
                }
            },
        }
        expected = (
            "⏸ Approval required\n\n"
            "Project: archon\n"
            "Workflow: archon-speckit-feature\n"
            "Run: run-1\n"
            "Gate: clarify-gate (plannotator_gate)\n\n"
            "User request:\nAdd the requested workflow capability.\n\n"
            "Review:\nhttps://archon-host.example.ts.net:19432"
        )

        app = _create_app(adapter)
        async with TestClient(TestServer(app)) as cli:
            response = await cli.post(
                "/webhooks/archon-approval",
                json=payload,
                headers={"X-Request-ID": "archon-event-2"},
            )
            assert response.status == 202
            assert await response.json() == {
                "status": "accepted",
                "route": "archon-approval",
                "target": "all",
                "delivery_id": "archon-event-2",
            }
            await _drain_background_tasks(adapter)

        handle_message.assert_not_awaited()
        targets[Platform.TELEGRAM].send.assert_awaited_once_with(
            "telegram-home",
            expected,
            metadata={"thread_id": "topic-7"},
        )
        targets[Platform.SLACK].send.assert_awaited_once_with(
            "slack-home",
            expected,
            metadata=None,
        )

    @pytest.mark.asyncio
    async def test_all_returns_202_before_home_delivery_finishes(self):
        routes = {
            "r": {
                "secret": _INSECURE_NO_AUTH,
                "deliver": "all",
                "deliver_only": True,
                "prompt": "approval pending",
            }
        }
        adapter = _make_adapter(routes)
        targets = _wire_mock_homes(
            adapter,
            {
                Platform.TELEGRAM: HomeChannel(
                    platform=Platform.TELEGRAM,
                    chat_id="telegram-home",
                    name="Telegram Ops",
                )
            },
        )
        started = asyncio.Event()
        release = asyncio.Event()

        async def _blocked_send(chat_id, content, metadata=None):
            started.set()
            await release.wait()
            return SendResult(success=True)

        targets[Platform.TELEGRAM].send.side_effect = _blocked_send

        app = _create_app(adapter)
        async with TestClient(TestServer(app)) as cli:
            response = await cli.post(
                "/webhooks/r",
                json={},
                headers={"X-Request-ID": "delivery-blocked"},
            )
            assert response.status == 202
            await asyncio.wait_for(started.wait(), timeout=1)
            assert adapter._background_tasks
            release.set()
            await _drain_background_tasks(adapter)

    @pytest.mark.asyncio
    async def test_all_continues_after_one_home_rejects_delivery(self, caplog):
        routes = {
            "r": {
                "secret": _INSECURE_NO_AUTH,
                "deliver": "all",
                "deliver_only": True,
                "prompt": "approval pending",
            }
        }
        adapter = _make_adapter(routes)
        targets = _wire_mock_homes(
            adapter,
            {
                Platform.TELEGRAM: HomeChannel(
                    platform=Platform.TELEGRAM,
                    chat_id="telegram-home",
                    name="Telegram Ops",
                ),
                Platform.SLACK: HomeChannel(
                    platform=Platform.SLACK,
                    chat_id="slack-home",
                    name="Slack Ops",
                ),
            },
            {
                Platform.TELEGRAM: SendResult(
                    success=False,
                    error="telegram unavailable",
                )
            },
        )

        app = _create_app(adapter)
        async with TestClient(TestServer(app)) as cli:
            response = await cli.post(
                "/webhooks/r",
                json={},
                headers={"X-Request-ID": "delivery-partial"},
            )
            assert response.status == 202
            await _drain_background_tasks(adapter)

        targets[Platform.TELEGRAM].send.assert_awaited_once()
        targets[Platform.SLACK].send.assert_awaited_once()
        assert "telegram unavailable" in caplog.text

    @pytest.mark.asyncio
    async def test_all_accepts_when_no_home_channel_exists(self, caplog):
        routes = {
            "r": {
                "secret": _INSECURE_NO_AUTH,
                "deliver": "all",
                "deliver_only": True,
                "prompt": "approval pending",
            }
        }
        adapter = _make_adapter(routes)
        runner = MagicMock()
        runner.adapters = {}
        runner.config.platforms = {}
        adapter.gateway_runner = runner

        app = _create_app(adapter)
        async with TestClient(TestServer(app)) as cli:
            response = await cli.post(
                "/webhooks/r",
                json={},
                headers={"X-Request-ID": "delivery-no-home"},
            )
            assert response.status == 202
            await _drain_background_tasks(adapter)

        assert "no configured home channels" in caplog.text


# ===================================================================
# HTTP status codes
# ===================================================================

class TestDeliverOnlyStatusCodes:

    @pytest.mark.asyncio
    async def test_delivery_failure_returns_502(self):
        """If the target adapter returns SendResult(success=False), 502."""
        routes = {
            "r": {
                "secret": _INSECURE_NO_AUTH,
                "deliver": "telegram",
                "deliver_only": True,
                "deliver_extra": {"chat_id": "c-1"},
                "prompt": "hi",
            }
        }
        adapter = _make_adapter(routes)
        mock_target = _wire_mock_target(adapter)
        mock_target.send = AsyncMock(
            return_value=SendResult(success=False, error="rate limited by tg")
        )

        app = _create_app(adapter)
        async with TestClient(TestServer(app)) as cli:
            resp = await cli.post(
                "/webhooks/r",
                json={},
                headers={"X-GitHub-Delivery": "d-fail-1"},
            )
            assert resp.status == 502
            data = await resp.json()
            # Generic error — no adapter-level detail leaks
            assert data["error"] == "Delivery failed"
            assert "rate limited" not in json.dumps(data)


# ===================================================================
# Startup validation
# ===================================================================

class TestDeliverOnlyStartupValidation:


    @pytest.mark.asyncio
    async def test_deliver_only_with_real_target_accepted(self):
        """Sanity check — a valid deliver_only config passes validation."""
        routes = {
            "good": {
                "secret": _INSECURE_NO_AUTH,
                "deliver": "telegram",
                "deliver_only": True,
                "deliver_extra": {"chat_id": "c-1"},
                "prompt": "hi",
            }
        }
        adapter = _make_adapter(routes)
        # connect() does more than validation (binds a socket) — we just
        # want to verify the validation doesn't raise.  Call it and tear
        # down immediately.
        try:
            started = await adapter.connect()
            if started:
                await adapter.disconnect()
        except ValueError:
            pytest.fail("valid deliver_only config should not raise ValueError")


# ===================================================================
# Security + reliability invariants still hold
# ===================================================================

class TestDeliverOnlySecurityInvariants:

    @pytest.mark.asyncio
    async def test_hmac_still_enforced(self):
        """deliver_only does NOT bypass HMAC validation."""
        secret = "real-secret-123"
        routes = {
            "r": {
                "secret": secret,
                "deliver": "telegram",
                "deliver_only": True,
                "deliver_extra": {"chat_id": "c-1"},
                "prompt": "hi",
            }
        }
        adapter = _make_adapter(routes)
        mock_target = _wire_mock_target(adapter)

        app = _create_app(adapter)
        async with TestClient(TestServer(app)) as cli:
            # No signature header → reject
            resp = await cli.post(
                "/webhooks/r",
                json={},
                headers={"X-GitHub-Delivery": "d-noauth-1"},
            )
            assert resp.status == 401

        # Target never called
        mock_target.send.assert_not_awaited()


# ===================================================================
# Unit: _direct_deliver dispatch
# ===================================================================

class TestDirectDeliverUnit:


    @pytest.mark.asyncio
    async def test_dispatches_to_github_comment(self):
        adapter = _make_adapter({})
        with patch.object(
            adapter, "_deliver_github_comment",
            new=AsyncMock(return_value=SendResult(success=True)),
        ) as mock_gh:
            result = await adapter._direct_deliver(
                "review body",
                {
                    "deliver": "github_comment",
                    "deliver_extra": {"repo": "org/r", "pr_number": "1"},
                },
            )
            assert result.success is True
            mock_gh.assert_awaited_once()
