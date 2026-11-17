import asyncio
import logging
from datetime import datetime
from typing import final, override

from textual import work
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

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

ENOTIFY_HEALTH_API_BASE_URL = get_and_assert_env("ENOTIFY_HEALTH_API_BASE_URL")
ENOTIFY_HEALTH_API_KEY = get_and_assert_env("ENOTIFY_HEALTH_API_KEY")
ENOTIFY_HEALTH_WS_URI = get_and_assert_env("ENOTIFY_HEALTH_WS_URI")

ENOTIFY_BACKUPS_API_BASE_URL = get_and_assert_env("ENOTIFY_BACKUPS_API_BASE_URL")
ENOTIFY_BACKUPS_API_KEY = get_and_assert_env("ENOTIFY_BACKUPS_API_KEY")


SERVICES = [
    DetailLabelEntry(id="bot", name="Bot", icon="󰚩"),
    DetailLabelEntry(id="website", name="Website", icon=""),
    DetailLabelEntry(id="database", name="Database", icon=""),
]

@final
class ProjectCard(ProjectCardBase):
    backup_api_base_url = ENOTIFY_BACKUPS_API_BASE_URL
    backup_api_key = ENOTIFY_BACKUPS_API_KEY
    logger = logging.getLogger("projects.enotify")

    def __init__(self) -> None:
        super().__init__("Enotify")

        self.update_interval_secs = 5

        self.service_labels: dict[str, LabelWrapper] = {
            service.id: LabelWrapper(service) for service in SERVICES
        }

        self.services_section_heading = SectionHeading("Services")

        self.health_websocket = WebsocketClient(
            ENOTIFY_HEALTH_WS_URI,
            ENOTIFY_HEALTH_API_KEY,
            self.logger,
            asyncio.get_running_loop(),
            self.ws_update_service_statuses
        )
        self.health_websocket_task: asyncio.Task[bool] | None = None


    @override
    def compose(self) -> ComposeResult:
        yield self.services_section_heading

        with Vertical():
            for service in SERVICES:
                yield self.service_labels[service.id].set_loading()

        yield Static("", classes="vertical-spacer")


    @work
    async def on_mount(self) -> None:
        self.health_websocket_task = self.health_websocket.start()

    @work
    async def on_unmount(self) -> None:
        self.health_websocket.close()

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
