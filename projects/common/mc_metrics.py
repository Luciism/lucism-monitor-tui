from aiohttp import ClientSession
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class _MemoryUsageMetric(BaseModel):
    max: int
    used: int

class _McPlayer(BaseModel):
    model_config: ConfigDict = ConfigDict(alias_generator=to_camel)

    session_online_millis: int = Field()
    name: str
    uuid: str
    ping: int

class McServerMetricsData(BaseModel):
    model_config: ConfigDict = ConfigDict(alias_generator=to_camel)

    cpu_usage: float
    uptime_millis: int
    memory: _MemoryUsageMetric
    max_players: int
    online_players: int
    tps: float
    ping: int
    players: list[_McPlayer]
    server_address: str
    loaded_chunks: int
    timestamp: int

    def format_memory(self) -> str:
        used_mbs = round(self.memory.used / 1024 / 1024)
        max_mbs = round(self.memory.max / 1024 / 1024)

        return f"{used_mbs} / {max_mbs} MB"

    def format_uptime(self) -> str:
        if self.uptime_millis < 60 * 1000:
            return f"{round(self.uptime_millis / 1000)}s"
        elif self.uptime_millis < 60 * 60 * 1000:
            return f"{round(self.uptime_millis / 1000 / 60)}m"
        elif self.uptime_millis < 24 * 60 * 60 * 1000:
            return f"{round(self.uptime_millis / 1000 / 60 / 60)}h"
        else:
            return f"{round(self.uptime_millis / 1000 / 60 / 60 / 24)}d"


class McServerMetrics:
    def __init__(self, monitoring_base_url: str, x_api_key: str | None=None) -> None:
        self.monitoring_base_url: str = monitoring_base_url
        self._x_api_key: str | None = x_api_key

    async def get_current_metrics(self) -> McServerMetricsData:
        async with ClientSession() as session:
            res = await session.get(
                f"{self.monitoring_base_url}/metrics/current",
                headers={"x-api-key": self._x_api_key} if self._x_api_key else None
            )

            res.raise_for_status()

            data = await res.json()
            return McServerMetricsData.model_validate(data)
