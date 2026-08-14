#!/usr/bin/env python3
"""
Gemini Live WebSocket Proxy
===========================
Runs as a standalone asyncio server on port 8765.
The frontend connects to this proxy instead of Gemini directly.
The proxy authenticates to Gemini using the server-side API key.

Usage: python ws_proxy.py
"""
import asyncio
import json
import logging
import os
import sys

# Add the Django project to the path so we can read settings
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.conf import settings

import websockets
from websockets.server import WebSocketServerProtocol

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [ws_proxy] %(levelname)s %(message)s'
)
log = logging.getLogger('ws_proxy')

GEMINI_LIVE_URL = (
    "wss://generativelanguage.googleapis.com/ws/"
    "google.ai.generativelanguage.v1alpha."
    "GenerativeService.BidiGenerateContent"
    "?key={api_key}"
)

HOST = "0.0.0.0"
PORT = 8765


async def proxy_handler(client_ws: WebSocketServerProtocol):
    """
    Opens a Gemini Live WebSocket session for each incoming client connection.
    Bidirectionally proxies all messages between client and Gemini.
    """
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        await client_ws.close(1011, "GEMINI_API_KEY not configured on server")
        return

    gemini_url = GEMINI_LIVE_URL.format(api_key=api_key)
    client_addr = client_ws.remote_address
    log.info(f"[+] Client connected: {client_addr}")

    try:
        async with websockets.connect(
            gemini_url,
            max_size=10 * 1024 * 1024,      # 10 MB max message
            ping_interval=None,               # Gemini handles its own keep-alive
            additional_headers={"Origin": "https://generativelanguage.googleapis.com"},
        ) as gemini_ws:
            log.info(f"    Gemini session open for {client_addr}")

            async def client_to_gemini():
                """Relay messages from browser client → Gemini."""
                try:
                    async for msg in client_ws:
                        await gemini_ws.send(msg)
                except websockets.exceptions.ConnectionClosed:
                    pass
                finally:
                    await gemini_ws.close()

            async def gemini_to_client():
                """Relay messages from Gemini → browser client."""
                try:
                    async for msg in gemini_ws:
                        await client_ws.send(msg)
                except websockets.exceptions.ConnectionClosed:
                    pass
                finally:
                    await client_ws.close()

            # Run both relay tasks concurrently
            await asyncio.gather(
                asyncio.ensure_future(client_to_gemini()),
                asyncio.ensure_future(gemini_to_client()),
            )

    except websockets.exceptions.InvalidStatusCode as e:
        log.error(f"    Gemini rejected connection: {e.status_code} {e}")
        try:
            await client_ws.close(1011, f"Gemini error: {e.status_code}")
        except Exception:
            pass
    except Exception as e:
        log.error(f"    Proxy error for {client_addr}: {e}")
        try:
            await client_ws.close(1011, "Proxy error")
        except Exception:
            pass
    finally:
        log.info(f"[-] Client disconnected: {client_addr}")


async def main():
    log.info(f"Starting Gemini Live WebSocket Proxy on ws://{HOST}:{PORT}")
    async with websockets.serve(
        proxy_handler,
        HOST,
        PORT,
        max_size=10 * 1024 * 1024,
        ping_interval=20,
        ping_timeout=10,
    ):
        log.info("Proxy is running. Press Ctrl+C to stop.")
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Proxy stopped.")
