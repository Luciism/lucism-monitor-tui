import os
import json
import asyncio
import logging
import concurrent.futures
from datetime import datetime
from typing import Any, Callable, final, override
from collections.abc import Coroutine

import websocket
from textual import work
from textual.app import ComposeResult, App
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Label, Static, RichLog

from .common.environment import get_and_assert_env

from .style import Color
from .common.backup_schedule import update_backup_schedule_labels
from .project_card import (
    ProjectCardBase,
    DetailLabelEntry,
    SectionHeading,
    build_detail_label,
    LabelWrapper,
    ServiceStatus
)

STATALYTICS_HEALTH_API_BASE_URL = get_and_assert_env("STATALYTICS_HEALTH_API_BASE_URL")
STATALYTICS_HEALTH_API_KEY = get_and_assert_env("STATALYTICS_HEALTH_API_KEY")

STATALYTICS_BACKUPS_API_BASE_URL = get_and_assert_env("STATALYTICS_BACKUPS_API_BASE_URL")
STATALYTICS_BACKUPS_API_KEY = get_and_assert_env("STATALYTICS_BACKUPS_API_KEY")

type ServiceStatusAlias = dict[str, str | dict[str, str | dict[str, str]]]

@final
class HealthWebsocketClient(websocket.WebSocketApp):
    url: str = os.environ["STATALYTICS_HEALTH_WS_URL"]

    def __init__(
        self,
        logger: logging.Logger,
        event_loop: asyncio.AbstractEventLoop,
        on_status_receive: Callable[[ServiceStatusAlias], Coroutine[Any, Any, None]]
    ) -> None:
        self._on_status_receive = on_status_receive
        self.app_loop = event_loop
        self.logger: logging.Logger = logger

        headers = {"X-Api-Key": STATALYTICS_HEALTH_API_KEY}
        super().__init__(
            self.url,
            headers,
            on_message=HealthWebsocketClient.on_message,
            on_error=HealthWebsocketClient.on_error,
            on_close=HealthWebsocketClient.on_close,
            on_open=HealthWebsocketClient.on_open
        )


    @override
    def on_message(self, message: str) -> None:
        self.logger.debug("WebSocket message received: %s", message)

        try:
            status: ServiceStatusAlias = json.loads(message)
        except json.JSONDecodeError:
            self.logger.exception("Invalid health WebSocket message")
            status = {
                "status": "unhealthy",
                "timestamp": "none",
                "services": {
                    service.id: {"status": "unhealthy"} for service in SERVICES
                }
            }

        future = asyncio.run_coroutine_threadsafe(
            self._on_status_receive(status),
            self.app_loop,
        )
        future.add_done_callback(self._log_callback_error)

    def _log_callback_error(
        self,
        future: concurrent.futures.Future[None],
    ) -> None:
        try:
            future.result()
        except Exception:
            self.logger.exception("Async status callback failed")

    @override
    def on_error(self, error: str):
        self.logger.error(f"Health websocket error: {error}")

    @override
    def on_close(self, close_status_code: int, close_msg: str):
        self.logger.info(f"Health websocket closed with code '{close_status_code}': '{close_msg}'")

    @override
    def on_open(self):
        self.logger.info("Health websocket connection opened")

    def start(self) -> asyncio.Task[bool]:
        return asyncio.create_task(asyncio.to_thread(self.run_forever, reconnect=5))
        # is_alive = self.run_forever(dispatcher=rel, reconnect=5)
        # rel.dispatch()


SERVICES = [
    DetailLabelEntry(id="bot", name="Bot", icon="󰚩"),
    DetailLabelEntry(id="trackers", name="Trackers", icon=""),
    DetailLabelEntry(id="utils", name="Utils", icon=""),
    DetailLabelEntry(id="website", name="Website", icon=""),
    DetailLabelEntry(id="renderer", name="Renderer", icon="󰋩"),
    DetailLabelEntry(id="redis", name="Redis", icon=""),
    DetailLabelEntry(id="skins", name="Skins", icon=""),
]


@final
class ProjectCard(ProjectCardBase):
    backup_api_base_url = STATALYTICS_BACKUPS_API_BASE_URL
    backup_api_key = STATALYTICS_BACKUPS_API_KEY
    logger = logging.getLogger("projects.statalytics")

    def __init__(self) -> None:
        super().__init__("Statalytics")
        self.set_border_color(Color.Loading)

        self.update_interval_secs = 5

        self.service_labels: dict[str, LabelWrapper] = {
            service.id: LabelWrapper(service) for service in SERVICES
        }

        self.services_section_heading = SectionHeading("Services")
        self.backups_section_heading = SectionHeading("Backups")

        self.last_backup_status_label = LabelWrapper(
            DetailLabelEntry("last_backup_status", "Last Backup Status", ""))
        self.last_backup_attempt_label = LabelWrapper(
            DetailLabelEntry("last_backup_attempt", "Last Backup Attempt", "󰥔"))
        self.next_backup_label = LabelWrapper(DetailLabelEntry("next_backup", "Next Backup", "󰥔"))

        self.health_websocket = HealthWebsocketClient(
            self.logger,
            asyncio.get_running_loop(),
            self.ws_update_service_statuses
        )
        self.health_websocket_task: asyncio.Task[bool] | None = None

    @override
    def compose(self) -> ComposeResult:
        yield self.services_section_heading

        with Vertical(classes="section-a"):
            for service in SERVICES:
                yield self.service_labels[service.id].set_loading()

        # yield Static("", classes="vertical-spacer-small")
        yield self.backups_section_heading

        with Vertical():
            yield self.last_backup_status_label.set_loading()
            yield self.last_backup_attempt_label.set_loading()
            yield self.next_backup_label.set_loading()


        yield Static("", classes="vertical-spacer")

        with Horizontal():
            yield Button("Create Backup", variant="primary")
            yield Button("Refresh All Info", variant="primary",)

    @work
    async def on_mount(self) -> None:
        self.health_websocket_task = self.health_websocket.start()


    async def ws_update_service_statuses(self, services_status: ServiceStatusAlias) -> None:
        overall_health = services_status["status"]

        match overall_health:
            case "healthy":
                self.set_border_color(Color.Running)
            case "degraded":
                self.set_border_color(Color.Degraded)
            case _:
                self.set_border_color(Color.Offline)

        for service in SERVICES:
            service_status = services_status["services"][service.id]["status"]
            if service_status == "healthy":
                status = ServiceStatus.as_healthy()
            else:
                status = ServiceStatus.as_unhealthy()

            self.service_labels[service.id].update_detail(status.status, Color(status.color))

        # TODO: use websocket
        _ = await update_backup_schedule_labels(self)

        now = datetime.now()

        self.services_section_heading.set_updated_at(now)
        self.backups_section_heading.set_updated_at(now)

