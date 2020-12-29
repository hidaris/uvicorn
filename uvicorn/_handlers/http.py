import asyncio
from typing import TYPE_CHECKING

from uvicorn.config import Config

if TYPE_CHECKING:  # pragma: no cover
    from uvicorn.server import ServerState

MAX_RECV = 65536


async def handle_http(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    server_state: "ServerState",
    config: Config,
) -> None:
    # Run transport/protocol session from streams.

    # Use a future to coordinate between the protocol and this handler task.
    # https://docs.python.org/3/library/asyncio-protocol.html#connecting-existing-sockets
    loop = asyncio.get_event_loop()
    connection_lost = loop.create_future()

    # Switch the protocol from the stream reader to our own HTTP protocol class.
    protocol = config.http_protocol_class(
        config=config,
        server_state=server_state,
        on_connection_lost=lambda: connection_lost.set_result(True),
    )
    transport = writer.transport
    transport.set_protocol(protocol)

    # Kick off the HTTP protocol.
    protocol.connection_made(transport)

    # HACK: Pass any data already in the read buffer.
    # The assumption here is that we haven't read any data off the stream reader
    # yet: all data that the client might have already sent since the connection has
    # been established is in the `_buffer`.
    data = reader._buffer  # type: ignore
    if data:
        protocol.data_received(data)

    # Let the transport run in the background. When closed, this future will complete
    # and we'll exit here.
    await connection_lost
