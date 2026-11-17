import asyncio
import logging
import typing
from typing import final, override
from datetime import datetime

from textual import work
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from .common.environment import get_and_assert_env
from .common.ws_client import WebsocketClient

from .style import Color
from .common.backup_schedule import BackupSchedule, ws_update_backup_schedule_labels
from .project_card import (
    ProjectCardBase,
    DetailLabelEntry,
    SectionHeading,
    LabelWrapper,
    ServiceStatus
)

STATALYTICS_HEALTH_API_BASE_URL = get_and_assert_env("STATALYTICS_HEALTH_API_BASE_URL")
STATALYTICS_HEALTH_WS_URI = get_and_assert_env("STATALYTICS_HEALTH_WS_URI")
STATALYTICS_HEALTH_API_KEY = get_and_assert_env("STATALYTICS_HEALTH_API_KEY")

STATALYTICS_BACKUPS_API_BASE_URL = get_and_assert_env("STATALYTICS_BACKUPS_API_BASE_URL")
STATALYTICS_BACKUPS_WS_URI = get_and_assert_env("STATALYTICS_BACKUPS_WS_URI")
STATALYTICS_BACKUPS_API_KEY = get_and_assert_env("STATALYTICS_BACKUPS_API_KEY")

type ServiceStatusAlias = dict[str, str | dict[str, str | dict[str, str]]]



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
            STATALYTICS_HEALTH_WS_URI,
            STATALYTICS_HEALTH_API_KEY,
            self.logger,
            asyncio.get_running_loop(),
            self.ws_update_service_statuses
        )
        self.health_websocket_task: asyncio.Task[bool] | None = None

        self.backups_websocket = WebsocketClient(
            STATALYTICS_BACKUPS_WS_URI,
            STATALYTICS_BACKUPS_API_KEY,
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

        yield self.backups_section_heading

        with Vertical():
            yield self.last_backup_status_label.set_loading()
            yield self.last_backup_attempt_label.set_loading()
            yield self.next_backup_label.set_loading()


        yield Static("", classes="vertical-spacer")

        # Prototype
        # with Horizontal():
        #     yield Button("Create Backup", variant="primary")
        #     yield Button("Refresh All Info", variant="primary",)

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
        services_status: ServiceStatusAlias | WebsocketClient.InvalidWsResponseSentinel
    ) -> None:
        if isinstance(services_status, WebsocketClient.InvalidWsResponseSentinel):
            services_status = {
                "status": "unhealthy",
                "timestamp": "none",
                "services": {
                    service.id: {"status": "unhealthy"} for service in SERVICES
                }
            }

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
        
        self.services_section_heading.set_updated_at(datetime.now())
        
    async def ws_update_backup_schedule(
        self,
        backup_schedule: dict[str, typing.Any] | WebsocketClient.InvalidWsResponseSentinel
    ) -> None:
        await ws_update_backup_schedule_labels(self, backup_schedule)
        self.backups_section_heading.set_updated_at(datetime.now())

