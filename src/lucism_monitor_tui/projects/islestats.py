import asyncio
import typing 
import logging
from datetime import datetime
from typing import final, override

from textual import work
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from .common.backup_schedule import ws_update_backup_schedule_labels
from .common.environment import get_and_assert_env
from .common.ws_client import WebsocketClient

from .style import Color
from .project_card import (
    ProjectCardBase,
    DetailLabelEntry,
    SectionHeading,
    LabelWrapper,
    ServiceStatus
)

ISLESTATS_HEALTH_API_BASE_URL = get_and_assert_env("ISLESTATS_HEALTH_API_BASE_URL")
ISLESTATS_HEALTH_API_KEY = get_and_assert_env("ISLESTATS_HEALTH_API_KEY")
ISLESTATS_HEALTH_WS_URI = get_and_assert_env("ISLESTATS_HEALTH_WS_URI")

ISLESTATS_BACKUPS_API_BASE_URL = get_and_assert_env("ISLESTATS_BACKUPS_API_BASE_URL")
ISLESTATS_BACKUPS_API_KEY = get_and_assert_env("ISLESTATS_BACKUPS_API_KEY")
ISLESTATS_BACKUPS_WS_URI = get_and_assert_env("ISLESTATS_BACKUPS_WS_URI")


SERVICES = [
    DetailLabelEntry(id="bot", name="Bot", icon="󰚩"),
    DetailLabelEntry(id="api", name="API", icon="󰞵"),
    DetailLabelEntry(id="website", name="Website", icon=""),
    DetailLabelEntry(id="database", name="Database", icon=""),
    DetailLabelEntry(id="linking_server", name="Linking Server", icon="󰍳"),
]

@final
class ProjectCard(ProjectCardBase):
    backup_api_base_url = ISLESTATS_BACKUPS_API_BASE_URL
    backup_api_key = ISLESTATS_BACKUPS_API_KEY
    logger = logging.getLogger("projects.islestats")

    def __init__(self) -> None:
        super().__init__("IsleStats")

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

        self.health_websocket = WebsocketClient(
            ISLESTATS_HEALTH_WS_URI,
            ISLESTATS_HEALTH_API_KEY,
            self.logger,
            asyncio.get_running_loop(),
            self.ws_update_service_statuses
        )
        self.health_websocket_task: asyncio.Task[bool] | None = None

        self.backups_websocket = WebsocketClient(
            ISLESTATS_BACKUPS_WS_URI,
            ISLESTATS_BACKUPS_API_KEY,
            self.logger,
            asyncio.get_running_loop(),
            self.ws_update_backup_schedule
        )
        self.backups_websocket_task: asyncio.Task[bool] | None = None

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


    @work
    async def on_mount(self) -> None:
        self.health_websocket_task = self.health_websocket.start()
        self.backups_websocket_task = self.backups_websocket.start()

    @work
    async def on_unmount(self) -> None:
        self.health_websocket.close()
        self.backups_websocket.close()


    async def ws_update_service_statuses(
        self,
        service_statuses: dict[str, dict[str, str]] | WebsocketClient.InvalidWsResponseSentinel
    ) -> None:
        if isinstance(service_statuses, WebsocketClient.InvalidWsResponseSentinel):
            service_statuses = { "services": { service.id: "unhealthy" for service in SERVICES } }

        total_services = len(service_statuses["services"])
        healthy_services = len([s for s in service_statuses["services"].values() if s == "healthy"])

        # All services are critical
        overall_health = "healthy" if healthy_services == total_services else "unhealthy"

        match overall_health:
            case "healthy":
                self.set_border_color(Color.Running)
            case _:
                self.set_border_color(Color.Offline)

        for service in SERVICES:
            service_status = service_statuses["services"][service.id]
            
            if service_status == "healthy":
                status = ServiceStatus.as_healthy()
            else:
                status = ServiceStatus.as_unhealthy()

            self.service_labels[service.id].update_detail(status.status, Color(status.color))

        self.services_section_heading.set_updated_at(datetime.now())


    async def ws_update_backup_schedule(
        self,
        backup_schedule: dict[str, typing.Any] | WebsocketClient.InvalidWsResponseSentinel
    ) -> None:
        await ws_update_backup_schedule_labels(self, backup_schedule)
        self.backups_section_heading.set_updated_at(datetime.now())
