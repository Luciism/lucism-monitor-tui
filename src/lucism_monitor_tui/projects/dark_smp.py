import typing
import asyncio
import logging
from datetime import datetime
from typing import final, override

from aiohttp import ClientError
from textual import work
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from .common.backup_schedule import ws_update_backup_schedule_labels
from .common.ws_client import WebsocketClient
from .common.mc_metrics import McServerMetrics
from .common.environment import get_and_assert_env

from .style import Color
from .project_card import ProjectCardBase, LabelWrapper, DetailLabelEntry, SectionHeading


DARK_SMP_METRICS_SERVER_BASE_URL = get_and_assert_env("DARK_SMP_METRICS_SERVER_BASE_URL")
DARK_SMP_METRICS_SERVER_API_KEY = get_and_assert_env("DARK_SMP_METRICS_SERVER_API_KEY")

DARK_SMP_BACKUPS_API_BASE_URL = get_and_assert_env("DARK_SMP_BACKUPS_API_BASE_URL")
DARK_SMP_BACKUPS_API_KEY = get_and_assert_env("DARK_SMP_BACKUPS_API_KEY")
DARK_SMP_BACKUPS_WS_URI = get_and_assert_env("DARK_SMP_BACKUPS_WS_URI")


@final
class ProjectCard(ProjectCardBase):
    backup_api_base_url = DARK_SMP_BACKUPS_API_BASE_URL 
    backup_api_key = DARK_SMP_BACKUPS_API_KEY
    logger = logging.getLogger("projects.dark_smp")


    def __init__(self) -> None:
        super().__init__("Dark SMP")

        self.update_interval_secs = 5
        self.next_backup_time: datetime | None = None

        self.metrics_section_heading = SectionHeading("Metrics")
        self.backups_section_heading = SectionHeading("Backups")

        self.status_label = LabelWrapper(DetailLabelEntry("status", "Status", ""))
        self.uptime_label = LabelWrapper(DetailLabelEntry("uptime", "Uptime", "󰥔"))
        self.tps_label = LabelWrapper(DetailLabelEntry("tps", "TPS", "󰓅"))
        self.players_label = LabelWrapper(DetailLabelEntry("players", "Players", ""))
        self.loaded_chunks_label = LabelWrapper(DetailLabelEntry("loaded_chunks", "Loaded Chunks", ""))
        self.memory_label = LabelWrapper(DetailLabelEntry("memory", "Memory", "󰍛"))

        self.last_backup_status_label = LabelWrapper(
            DetailLabelEntry("last_backup_status", "Last Backup Status", ""))
        self.last_backup_attempt_label = LabelWrapper(
            DetailLabelEntry("last_backup_attempt", "Last Backup Attempt", "󰥔"))
        self.next_backup_label = LabelWrapper(DetailLabelEntry("next_backup", "Next Backup", "󰥔"))

        self.backups_websocket = WebsocketClient(
            DARK_SMP_BACKUPS_WS_URI,
            DARK_SMP_BACKUPS_API_KEY,
            self.logger,
            asyncio.get_running_loop(),
            self.ws_update_backup_schedule
        )
        self.backups_websocket_task: asyncio.Task[bool] | None = None


    @override
    def compose(self) -> ComposeResult:
        yield self.metrics_section_heading

        with Vertical(classes="section-a"):
            yield self.status_label.set_loading()
            yield self.tps_label.set_loading()
            yield self.memory_label.set_loading()
            yield self.uptime_label.set_loading()
            yield self.players_label.set_loading()
            yield self.loaded_chunks_label.set_loading()


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

        # self.health_websocket_task = self.health_websocket.start()
        self.backups_websocket_task = self.backups_websocket.start()

    @work
    async def on_unmount(self) -> None:
        # self.health_websocket.close()
        self.backups_websocket.close()

    async def update_server_metrics(self) -> None:
        try:
            metrics = await McServerMetrics(
                DARK_SMP_METRICS_SERVER_BASE_URL, DARK_SMP_METRICS_SERVER_API_KEY
            ).get_current_metrics()
        except ClientError as exc:
            self.logger.error("Failed to get metrics", exc_info=exc)
            metrics = None

        if metrics:
            if metrics.tps >= 19:
                tps_color = Color.Running
            elif metrics.tps < 10:
                tps_color = Color.Offline
            else:
                tps_color = Color.Degraded
            self.set_border_color(tps_color)

            if metrics.memory.used / (metrics.memory.max or 1) > 0.8:
                memory_color = Color.Offline
            elif metrics.memory.used / (metrics.memory.max or 1) > 0.65:
                memory_color = Color.Degraded
            else:
                memory_color = Color.Running

            self.status_label.update_detail("Online", Color.Running)
            self.uptime_label.update_detail(metrics.format_uptime(), Color.Accent)
            self.tps_label.update_detail(str(round(metrics.tps, 2)), tps_color)
            self.players_label.update_detail(str(metrics.online_players), Color.Accent)
            self.loaded_chunks_label.update_detail(str(metrics.loaded_chunks), Color.Accent)
            self.memory_label.update_detail(metrics.format_memory(), memory_color)

        else:
            self.set_border_color(Color.Offline)
            self.status_label.update_detail("Offline", Color.Offline)
            self.uptime_label.update_detail("N/A", Color.Offline)
            self.tps_label.update_detail("N/A", Color.Offline)
            self.players_label.update_detail("N/A", Color.Offline)
            self.loaded_chunks_label.update_detail("N/A", Color.Offline)
            self.memory_label.update_detail("N/A", Color.Offline)


    async def update_info(self) -> None:
        await self.update_server_metrics()
        self.metrics_section_heading.set_updated_at(datetime.now())


    async def ws_update_backup_schedule(
        self,
        backup_schedule: dict[str, typing.Any] | WebsocketClient.InvalidWsResponseSentinel
    ) -> None:
        await ws_update_backup_schedule_labels(self, backup_schedule)
        self.backups_section_heading.set_updated_at(datetime.now())
