import logging
from datetime import datetime
from typing import final, override

from aiohttp import ClientSession, ClientError
from textual import work
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Label, Static

from .common.backup_schedule import update_backup_schedule_labels
from .common.environment import get_and_assert_env

from .style import Color
from .project_card import (
    ProjectCardBase,
    DetailLabelEntry,
    SectionHeading,
    build_detail_label,
    LabelWrapper,
    ServiceStatus
)

ISLESTATS_HEALTH_API_BASE_URL = get_and_assert_env("ISLESTATS_HEALTH_API_BASE_URL")
ISLESTATS_HEALTH_API_KEY = get_and_assert_env("ISLESTATS_HEALTH_API_KEY")

ISLESTATS_BACKUPS_API_BASE_URL = get_and_assert_env("ISLESTATS_BACKUPS_API_BASE_URL")
ISLESTATS_BACKUPS_API_KEY = get_and_assert_env("ISLESTATS_BACKUPS_API_KEY")


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
        await self.update_info()
        _ = self.set_interval(self.update_interval_secs, self.update_info)

    async def get_service_status(self) -> dict[str, dict[str, str]]:
        try:
            async with ClientSession(raise_for_status=True) as session:
                res = await session.get(
                    f"{ISLESTATS_HEALTH_API_BASE_URL}/health",
                    headers={
                        "X-Api-Key": ISLESTATS_HEALTH_API_KEY
                    })
                return await res.json()
        except ClientError:
            return { "services": { service.id: "unhealthy" for service in SERVICES } }

    async def update_service_statuses(self) -> None:
        service_statuses = await self.get_service_status()
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

    async def update_info(self) -> None:
        await self.update_service_statuses()
        _ = await update_backup_schedule_labels(self)

        now = datetime.now()
        self.services_section_heading.set_updated_at(now)
        self.backups_section_heading.set_updated_at(now)
