"""Notification step — send a message to Slack, Microsoft Teams, or Telegram.

Config:
    platform     "slack" | "teams" | "telegram"
    message      Jinja2 template for the message body
    title        Optional title shown as bold header (Teams / Telegram)

    # Slack + Teams:
    webhook_url  Incoming-webhook URL

    # Telegram:
    bot_token    Bot token from @BotFather
    chat_id      Target chat ID (group, channel, or user)
    parse_mode   "HTML" (default) or "Markdown"
"""
import logging
from typing import Any

from flowforge.steps.base import BaseStep, StepResult

logger = logging.getLogger(__name__)


class NotificationStep(BaseStep):
    step_type = 'notification'

    def run(self, context: dict[str, Any]) -> StepResult:
        from flowforge.engine.context import render_guarded

        platform = str(self.config.get('platform', 'slack')).lower()
        raw_msg  = str(self.config.get('message', ''))
        title    = str(self.config.get('title', ''))

        try:
            message = render_guarded(raw_msg, context, sink='notification message')
            if title:
                title = render_guarded(title, context, sink='notification title')
        except Exception as e:
            logger.exception("Notification step failed")
            return StepResult(success=False, error=str(e))

        try:
            if platform == 'slack':
                return self._send_slack(message)
            if platform == 'teams':
                return self._send_teams(message, title)
            if platform == 'telegram':
                return self._send_telegram(message, title, context)
            return StepResult(success=False, error=f"Unknown notification platform: {platform!r}")
        except Exception as e:
            logger.exception("Notification step failed")
            return StepResult(success=False, error=str(e))

    # ── Slack ─────────────────────────────────────────────────────────────────

    def _send_slack(self, message: str) -> StepResult:
        webhook_url = str(self.config.get('webhook_url', '')).strip()
        if not webhook_url:
            return StepResult(success=False, error='webhook_url is required for Slack notifications')

        from flowforge.net_guard import UnsafeUrlError, assert_public_url
        try:
            assert_public_url(webhook_url)
        except UnsafeUrlError as e:
            return StepResult(success=False, error=str(e))

        import json
        import urllib.error
        import urllib.request
        body = json.dumps({'text': message}).encode()
        req  = urllib.request.Request(webhook_url, data=body, headers={'Content-Type': 'application/json'}, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=10):  # nosec B310
                pass
        except urllib.error.HTTPError as e:
            resp_body = e.read().decode()[:200]
            return StepResult(success=False, error=f"Slack webhook HTTP {e.code}: {resp_body}")
        logger.info("Slack notification sent")
        return StepResult(success=True, logs=f"Sent to Slack: {message[:80]}")

    # ── Microsoft Teams ────────────────────────────────────────────────────────

    def _send_teams(self, message: str, title: str) -> StepResult:
        webhook_url = str(self.config.get('webhook_url', '')).strip()
        if not webhook_url:
            return StepResult(success=False, error='webhook_url is required for Teams notifications')

        from flowforge.net_guard import UnsafeUrlError, assert_public_url
        try:
            assert_public_url(webhook_url)
        except UnsafeUrlError as e:
            return StepResult(success=False, error=str(e))

        import json
        import urllib.error
        import urllib.request

        # Teams Incoming Webhook expects Adaptive Card or legacy MessageCard
        payload: dict = {'type': 'message'}
        if title:
            payload['summary'] = title
            payload['sections'] = [{'activityTitle': title, 'activityText': message}]
            payload['@type']    = 'MessageCard'
            payload['@context'] = 'https://schema.org/extensions'
        else:
            payload['@type']    = 'MessageCard'
            payload['@context'] = 'https://schema.org/extensions'
            payload['text']     = message

        body = json.dumps(payload).encode()
        req  = urllib.request.Request(webhook_url, data=body, headers={'Content-Type': 'application/json'}, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=10):  # nosec B310
                pass
        except urllib.error.HTTPError as e:
            resp_body = e.read().decode()[:200]
            return StepResult(success=False, error=f"Teams webhook HTTP {e.code}: {resp_body}")
        logger.info("Teams notification sent")
        return StepResult(success=True, logs=f"Sent to Teams: {message[:80]}")

    # ── Telegram ──────────────────────────────────────────────────────────────

    def _send_telegram(self, message: str, title: str, context: dict) -> StepResult:
        bot_token  = str(self.config.get('bot_token', '')).strip()
        chat_id    = str(self.config.get('chat_id', '')).strip()
        parse_mode = str(self.config.get('parse_mode', 'HTML'))

        if not bot_token:
            return StepResult(success=False, error='bot_token is required for Telegram notifications')
        if not chat_id:
            return StepResult(success=False, error='chat_id is required for Telegram notifications')

        import json
        import urllib.error
        import urllib.parse
        import urllib.request

        text = f'<b>{title}</b>\n\n{message}' if title and parse_mode == 'HTML' else (
            f'*{title}*\n\n{message}' if title else message
        )

        url  = f'https://api.telegram.org/bot{bot_token}/sendMessage'
        body = json.dumps({'chat_id': chat_id, 'text': text, 'parse_mode': parse_mode}).encode()
        req  = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'}, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=10):  # nosec B310
                pass
        except urllib.error.HTTPError as e:
            resp_body = e.read().decode()[:200]
            return StepResult(success=False, error=f"Telegram API HTTP {e.code}: {resp_body}")
        logger.info("Telegram notification sent to chat %s", chat_id)
        return StepResult(success=True, logs=f"Sent to Telegram chat {chat_id}: {message[:80]}")
