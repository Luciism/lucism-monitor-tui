import json
import asyncio
import logging
import concurrent.futures
import typing
from typing import  Callable, final, override
from collections.abc import Coroutine

from typing_extensions import Sentinel
import websocket


@final
class WebsocketClient(websocket.WebSocketApp):
    class InvalidWsResponseSentinel(Sentinel): ...
    INVALID_WS_RESPONSE_SENTINEL = InvalidWsResponseSentinel("invalid_ws_response_sentinel")

    def __init__(
        self,
        uri: str,
        api_key: str,
        logger: logging.Logger,
        event_loop: asyncio.AbstractEventLoop,
        on_status_receive: Callable[
            [typing.Any | InvalidWsResponseSentinel],
            Coroutine[typing.Any, typing.Any, None]
        ]
    ) -> None:
        self._on_status_receive = on_status_receive
        self.app_loop = event_loop
        self.logger: logging.Logger = logger

        headers = {"X-Api-Key": api_key}
        super().__init__(
            uri,
            headers,
            on_message=WebsocketClient.on_message,
            on_error=WebsocketClient.on_error,
            on_close=WebsocketClient.on_close,
            on_open=WebsocketClient.on_open,
            on_reconnect=WebsocketClient.on_reconnect
        )


    @override
    def on_message(self, message: str) -> None:
        self.logger.debug("WebSocket message received: %s", message)

        try:
            status = json.loads(message)
        except json.JSONDecodeError:
            self.logger.exception("Invalid health WebSocket message")
            status = self.INVALID_WS_RESPONSE_SENTINEL

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

        future = asyncio.run_coroutine_threadsafe(
            self._on_status_receive(self.INVALID_WS_RESPONSE_SENTINEL),
            self.app_loop,
        )
        future.add_done_callback(self._log_callback_error)

    @override
    def on_close(self, close_status_code: int, close_msg: str):
        self.logger.info(f"Health websocket closed with code '{close_status_code}': '{close_msg}'")

    @override
    def on_reconnect(self):
        pass

    @override
    def on_open(self):
        self.logger.info("Health websocket connection opened")

    def start(self) -> asyncio.Task[bool]:
        return asyncio.create_task(asyncio.to_thread(self.run_forever, reconnect=5))

