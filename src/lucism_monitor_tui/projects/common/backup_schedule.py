from datetime import datetime
from dataclasses import dataclass
import logging
from typing import Protocol

from aiohttp import ClientSession, ClientError
from pydantic import BaseModel

from ..project_card import LabelWrapper
from ..style import Color

@dataclass
class _BackupScheduleNextBackup(BaseModel):
    timestamp: int
    in_progress: bool

class BackupSchedule(BaseModel):
    last_successful_backup_timestamp: int | None
    next_backup: _BackupScheduleNextBackup
    last_backup_status: str

    @staticmethod
    async def fetch_backup_schedule(api_base_url: str, api_key: str) -> 'BackupSchedule':
        async with ClientSession() as session:
            res = await session.get(
                f"{api_base_url}/backups/schedule", headers={ "X-Api-Key": api_key }
            )
            res.raise_for_status()

            data = await res.json()
            return BackupSchedule.model_validate(data)


    def format_next_backup(self) -> str:
        if self.next_backup.in_progress:
            return "In Progress"

        next_backup_delta = self.next_backup.timestamp - datetime.now().timestamp()

        if next_backup_delta < 60:
            return f"in {round(next_backup_delta)}s"
        
        if next_backup_delta < 60 * 60:
            return f"in {round(next_backup_delta / 60)}m"
        
        if next_backup_delta < 24 * 60 * 60:
            return f"in {round(next_backup_delta / 60 / 60)}h"
        
        return f"in {round(next_backup_delta / 60 / 60 / 24)}d"

    def format_last_successful_backup(self):
        if self.last_successful_backup_timestamp is None:
            return "N/A"

        last_success_delta = datetime.now().timestamp() - self.last_successful_backup_timestamp

        if last_success_delta < 60:
            return "Just now"
        
        if last_success_delta < 60 * 60:
            return f"{round(last_success_delta / 60)}m ago"
        
        if last_success_delta < 24 * 60 * 60:
            return f"{round(last_success_delta / 60 / 60)}h ago"
        
        return f"{round(last_success_delta / 60 / 60 / 24)}d ago"


class ProjectCardWithBackupSchedule(Protocol):
    last_backup_status_label: LabelWrapper
    last_backup_attempt_label: LabelWrapper
    next_backup_label: LabelWrapper

    logger: logging.Logger
    backup_api_base_url: str
    backup_api_key: str

async def update_backup_schedule_labels(
    self: ProjectCardWithBackupSchedule,
) -> None:
        try:
            self.logger.debug("Starting to fetch backup schedule")
            backup_schedule = await BackupSchedule.fetch_backup_schedule(
                self.backup_api_base_url, self.backup_api_key
            )
            self.logger.debug("Backup schedule fetched")
        except ClientError as exc:
            self.logger.error("Failed to get backup schedule", exc_info=exc)
            msg = "Fetch failed"

            self.next_backup_label.update_detail(msg, Color.Offline)
            self.last_backup_attempt_label.update_detail(msg, Color.Offline)
            self.last_backup_status_label.update_detail(msg, Color.Offline)
            return

        if backup_schedule.next_backup.in_progress:
            self.next_backup_label.update_detail(
                "In Progress",
                Color.Running
            )
        else:
            self.next_backup_label.update_detail(
                backup_schedule.format_next_backup(),
                Color.Accent
            )

        self.last_backup_attempt_label.update_detail(
            backup_schedule.format_last_successful_backup(),
            Color.Accent
        )

        match backup_schedule.last_backup_status:
            case "created":
                self.last_backup_status_label.update_detail(
                    "Created",
                    Color.Running
                )
            case "failed":
                self.last_backup_status_label.update_detail(
                    "Failed",
                    Color.Offline
                )
            case _:
                self.last_backup_status_label.update_detail(
                    "Unknown",
                    Color.Loading
                )

