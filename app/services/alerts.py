from __future__ import annotations

import json
from abc import ABC, abstractmethod

import aiosmtplib
import httpx

from app.config import settings
from app.models import DashboardState, Severity


class AlertSink(ABC):
    @abstractmethod
    async def send(self, state: DashboardState) -> None: ...


class ConsoleSink(AlertSink):
    async def send(self, state: DashboardState) -> None:
        print(f"[ALERT][{state.severity.value}] {state.overall_score}: {[a.title for a in state.alerts]}")


class SlackSink(AlertSink):
    async def send(self, state: DashboardState) -> None:
        if not settings.alert_slack_webhook:
            return
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(settings.alert_slack_webhook, json={
                "text": f"{state.severity.value.upper()} {state.overall_score}: {state.alerts[0].title}"
            })


class WhatsAppSink(AlertSink):
    async def send(self, state: DashboardState) -> None:
        if (
            not settings.whatsapp_access_token
            or not settings.whatsapp_phone_number_id
            or not settings.whatsapp_to_number
        ):
            return
        url = f"https://graph.facebook.com/v23.0/{settings.whatsapp_phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": settings.whatsapp_to_number,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": f"PCRW {state.severity.value.upper()} {state.overall_score}: {state.alerts[0].title}",
            },
        }
        headers = {
            "Authorization": f"Bearer {settings.whatsapp_access_token}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(url, json=payload, headers=headers)


class EmailSink(AlertSink):
    async def send(self, state: DashboardState) -> None:
        if not settings.smtp_host or not settings.alert_email_to:
            return
        message = (
            f"Subject: PCRW Alert {state.severity.value.upper()}\n"
            f"To: {settings.alert_email_to}\n"
            f"\n"
            f"Score: {state.overall_score}\n"
            f"Top alert: {state.alerts[0].title}\n"
            f"Payload: {json.dumps(state.model_dump(mode='json'), indent=2)}"
        )
        await aiosmtplib.send(
            message=message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username or None,
            password=settings.smtp_password or None,
            start_tls=True,
        )


class AlertManager:
    def __init__(self) -> None:
        self.sinks: list[AlertSink] = []
        if settings.alert_console_enabled:
            self.sinks.append(ConsoleSink())
        self.sinks.append(SlackSink())
        self.sinks.append(WhatsAppSink())
        self.sinks.append(EmailSink())

    async def maybe_send(self, state: DashboardState) -> None:
        if state.severity not in {Severity.red, Severity.deep_red}:
            return
        for sink in self.sinks:
            try:
                await sink.send(state)
            except Exception as exc:
                print(f"Alert sink failed: {exc}")
