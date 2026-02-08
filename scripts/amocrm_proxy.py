#!/usr/bin/env python3
"""Minimal HTTP CONNECT proxy for amoCRM API.

Allows the Docker container to reach amoCRM via the host's network (and VPN).
Run on the host: python3 scripts/amocrm_proxy.py
Then set AMOCRM_PROXY=http://host.docker.internal:8899 in docker-compose.yml.
"""

import asyncio
import logging
import sys


logging.basicConfig(level=logging.INFO, format="%(asctime)s [proxy] %(message)s")
logger = logging.getLogger(__name__)

LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8899


async def _forward(src: asyncio.StreamReader, dst: asyncio.StreamWriter):
    try:
        while True:
            data = await src.read(65536)
            if not data:
                break
            dst.write(data)
            await dst.drain()
    except (ConnectionResetError, BrokenPipeError, asyncio.CancelledError):
        pass
    finally:
        try:
            dst.close()
        except Exception:
            pass


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    try:
        header = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=10)
    except (asyncio.TimeoutError, asyncio.IncompleteReadError):
        writer.close()
        return

    first_line = header.split(b"\r\n")[0].decode()
    parts = first_line.split()
    if len(parts) < 3 or parts[0] != "CONNECT":
        writer.write(b"HTTP/1.1 405 Method Not Allowed\r\n\r\n")
        writer.close()
        return

    target = parts[1]
    if ":" in target:
        host, port_str = target.rsplit(":", 1)
        port = int(port_str)
    else:
        host, port = target, 443

    try:
        t_reader, t_writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=15)
    except Exception as e:
        logger.warning(f"Cannot connect to {host}:{port}: {e}")
        writer.write(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
        writer.close()
        return

    logger.info(f"CONNECT {host}:{port}")
    writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
    await writer.drain()

    await asyncio.gather(
        _forward(reader, t_writer),
        _forward(t_reader, writer),
    )


async def main():
    server = await asyncio.start_server(handle_client, LISTEN_HOST, LISTEN_PORT)
    logger.info(f"amoCRM proxy listening on {LISTEN_HOST}:{LISTEN_PORT}")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Proxy stopped")
