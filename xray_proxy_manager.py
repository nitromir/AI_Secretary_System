#!/usr/bin/env python3
"""
VLESS Proxy Manager using xray-core.

Provides VLESS proxy support for services that need to bypass network restrictions.
Currently used by GeminiProvider to route requests through a VLESS proxy.
"""

import json
import logging
import os
import shutil
import signal
import socket
import subprocess
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlparse


logger = logging.getLogger(__name__)


@dataclass
class VLESSConfig:
    """Parsed VLESS URL configuration."""

    uuid: str
    address: str
    port: int
    # Security settings
    security: str = "none"  # none, tls, reality
    sni: str = ""
    fingerprint: str = "chrome"
    # Reality settings
    public_key: str = ""
    short_id: str = ""
    spider_x: str = ""
    # Transport settings
    transport_type: str = "tcp"  # tcp, ws, grpc, http
    ws_path: str = ""
    ws_host: str = ""
    grpc_service_name: str = ""
    # Flow (for XTLS)
    flow: str = ""
    # Description
    remark: str = ""


def parse_vless_url(vless_url: str) -> VLESSConfig:
    """
    Parse a VLESS URL into a VLESSConfig object.

    VLESS URL format:
    vless://uuid@host:port?security=reality&pbk=xxx&sid=xxx&type=tcp&flow=xtls-rprx-vision#remark

    Args:
        vless_url: VLESS URL string

    Returns:
        VLESSConfig object

    Raises:
        ValueError: If URL is invalid
    """
    if not vless_url.startswith("vless://"):
        raise ValueError("URL must start with vless://")

    # Parse URL
    parsed = urlparse(vless_url)

    if not parsed.username:
        raise ValueError("UUID not found in VLESS URL")
    if not parsed.hostname:
        raise ValueError("Host not found in VLESS URL")
    if not parsed.port:
        raise ValueError("Port not found in VLESS URL")

    # Parse query parameters
    params = parse_qs(parsed.query)

    def get_param(key: str, default: str = "") -> str:
        values = params.get(key, [default])
        return values[0] if values else default

    # Extract remark from fragment
    remark = parsed.fragment or ""

    config = VLESSConfig(
        uuid=parsed.username,
        address=parsed.hostname,
        port=parsed.port,
        security=get_param("security", "none"),
        sni=get_param("sni", parsed.hostname),
        fingerprint=get_param("fp", "chrome"),
        public_key=get_param("pbk", ""),
        short_id=get_param("sid", ""),
        spider_x=get_param("spx", ""),
        transport_type=get_param("type", "tcp"),
        ws_path=get_param("path", ""),
        ws_host=get_param("host", ""),
        grpc_service_name=get_param("serviceName", ""),
        flow=get_param("flow", ""),
        remark=remark,
    )

    return config


def generate_xray_config(
    vless_config: VLESSConfig, socks_port: int = 10808, http_port: int = 10809
) -> dict:
    """
    Generate xray-core JSON configuration from VLESS config.

    Args:
        vless_config: Parsed VLESS configuration
        socks_port: Local SOCKS5 proxy port
        http_port: Local HTTP proxy port

    Returns:
        xray-core configuration dict
    """
    # Build stream settings
    stream_settings: dict = {"network": vless_config.transport_type}

    # Security settings
    if vless_config.security == "tls":
        stream_settings["security"] = "tls"
        stream_settings["tlsSettings"] = {
            "serverName": vless_config.sni,
            "fingerprint": vless_config.fingerprint,
            "allowInsecure": False,
        }
    elif vless_config.security == "reality":
        stream_settings["security"] = "reality"
        stream_settings["realitySettings"] = {
            "serverName": vless_config.sni,
            "fingerprint": vless_config.fingerprint,
            "publicKey": vless_config.public_key,
            "shortId": vless_config.short_id,
            "spiderX": vless_config.spider_x,
        }

    # Transport settings
    if vless_config.transport_type == "ws":
        stream_settings["wsSettings"] = {
            "path": vless_config.ws_path or "/",
            "headers": {"Host": vless_config.ws_host or vless_config.address},
        }
    elif vless_config.transport_type == "grpc":
        stream_settings["grpcSettings"] = {
            "serviceName": vless_config.grpc_service_name,
            "multiMode": False,
        }
    elif vless_config.transport_type == "tcp":
        stream_settings["tcpSettings"] = {"header": {"type": "none"}}

    # Build VLESS user
    vless_user: dict = {"id": vless_config.uuid, "encryption": "none"}
    if vless_config.flow:
        vless_user["flow"] = vless_config.flow

    # Build outbound
    outbound = {
        "tag": "proxy",
        "protocol": "vless",
        "settings": {
            "vnext": [
                {
                    "address": vless_config.address,
                    "port": vless_config.port,
                    "users": [vless_user],
                }
            ]
        },
        "streamSettings": stream_settings,
    }

    # Full xray config
    config = {
        "log": {"loglevel": "warning"},
        "inbounds": [
            {
                "tag": "socks-in",
                "port": socks_port,
                "listen": "127.0.0.1",
                "protocol": "socks",
                "settings": {"auth": "noauth", "udp": True},
                "sniffing": {"enabled": True, "destOverride": ["http", "tls"]},
            },
            {
                "tag": "http-in",
                "port": http_port,
                "listen": "127.0.0.1",
                "protocol": "http",
                "settings": {"timeout": 60},
            },
        ],
        "outbounds": [
            outbound,
            {"tag": "direct", "protocol": "freedom"},
            {"tag": "block", "protocol": "blackhole"},
        ],
        "routing": {
            "domainStrategy": "AsIs",
            "rules": [
                # Route all traffic through proxy
                {"type": "field", "outboundTag": "proxy", "network": "tcp,udp"}
            ],
        },
    }

    return config


class XrayProxyManager:
    """
    Manages xray-core process for VLESS proxy.

    Usage:
        manager = XrayProxyManager()
        if manager.configure("vless://..."):
            with manager.proxy_environment():
                # HTTP requests will use proxy
                response = requests.get("https://example.com")
    """

    # Search paths for xray binary (priority order)
    XRAY_SEARCH_PATHS = [
        "./bin/xray",  # Local project directory
        "/usr/local/bin/xray",  # Common installation path
        "/usr/bin/xray",  # System path
    ]

    def __init__(self, socks_port: int = 10808, http_port: int = 10809):
        """
        Initialize XrayProxyManager.

        Args:
            socks_port: Local SOCKS5 proxy port
            http_port: Local HTTP proxy port
        """
        self.socks_port = socks_port
        self.http_port = http_port
        self.process: Optional[subprocess.Popen] = None
        self.config_file: Optional[Path] = None
        self.vless_config: Optional[VLESSConfig] = None
        self._xray_path: Optional[str] = None

    def find_xray_binary(self) -> Optional[str]:
        """
        Find xray binary in known locations.

        Returns:
            Path to xray binary or None if not found
        """
        if self._xray_path:
            return self._xray_path

        # Check predefined paths
        for path_str in self.XRAY_SEARCH_PATHS:
            p = Path(path_str)
            if p.is_file() and os.access(path_str, os.X_OK):
                self._xray_path = path_str
                logger.info(f"Found xray at: {path_str}")
                return path_str

        # Try which command
        try:
            result = subprocess.run(["which", "xray"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                path_str = result.stdout.strip()
                if path_str and Path(path_str).is_file():
                    self._xray_path = path_str
                    logger.info(f"Found xray via which: {path_str}")
                    return path_str
        except Exception:
            pass

        # Also check shutil.which
        path = shutil.which("xray")
        if path:
            self._xray_path = path
            logger.info(f"Found xray via shutil.which: {path}")
            return path

        logger.warning("xray binary not found")
        return None

    def is_xray_available(self) -> bool:
        """Check if xray binary is available."""
        return self.find_xray_binary() is not None

    def is_running(self) -> bool:
        """Check if xray process is currently running."""
        if self.process is None:
            return False
        return self.process.poll() is None

    def is_port_in_use(self, port: int) -> bool:
        """Check if a port is already in use."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("127.0.0.1", port)) == 0

    def configure(self, vless_url: str) -> bool:
        """
        Configure xray with VLESS URL.

        Args:
            vless_url: VLESS URL to configure

        Returns:
            True if configuration successful, False otherwise
        """
        if not vless_url:
            logger.warning("Empty VLESS URL provided")
            return False

        try:
            self.vless_config = parse_vless_url(vless_url)
            logger.info(
                f"Configured VLESS proxy: {self.vless_config.address}:{self.vless_config.port}"
            )
            return True
        except ValueError as e:
            logger.error(f"Invalid VLESS URL: {e}")
            return False

    def start(self) -> bool:
        """
        Start xray process.

        Returns:
            True if started successfully, False otherwise
        """
        if self.is_running():
            logger.info("xray is already running")
            return True

        if not self.vless_config:
            logger.error("No VLESS configuration. Call configure() first.")
            return False

        xray_path = self.find_xray_binary()
        if not xray_path:
            logger.warning("xray not found, proxy will not be used")
            return False

        # Check if ports are available
        if self.is_port_in_use(self.socks_port):
            logger.warning(f"SOCKS port {self.socks_port} is already in use")
            # Assume xray is already running
            return True
        if self.is_port_in_use(self.http_port):
            logger.warning(f"HTTP port {self.http_port} is already in use")
            return True

        try:
            # Generate config
            config = generate_xray_config(self.vless_config, self.socks_port, self.http_port)

            # Write config to temp file
            self.config_file = Path(tempfile.mktemp(suffix=".json", prefix="xray_"))
            self.config_file.write_text(json.dumps(config, indent=2))

            # Start xray process
            self.process = subprocess.Popen(
                [xray_path, "run", "-c", str(self.config_file)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Wait for startup
            time.sleep(0.5)

            if self.process.poll() is not None:
                # Process exited
                stderr = self.process.stderr.read().decode() if self.process.stderr else ""
                logger.error(f"xray failed to start: {stderr}")
                self._cleanup_config()
                return False

            # Verify port is listening
            for _ in range(10):
                if self.is_port_in_use(self.http_port):
                    logger.info(f"xray started, HTTP proxy on 127.0.0.1:{self.http_port}")
                    return True
                time.sleep(0.1)

            logger.warning("xray started but HTTP port not listening yet")
            return True

        except Exception as e:
            logger.error(f"Failed to start xray: {e}")
            self._cleanup_config()
            return False

    def stop(self):
        """Stop xray process."""
        if self.process:
            try:
                self.process.send_signal(signal.SIGTERM)
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            except Exception as e:
                logger.warning(f"Error stopping xray: {e}")
            finally:
                self.process = None

        self._cleanup_config()
        logger.info("xray stopped")

    def _cleanup_config(self):
        """Remove temporary config file."""
        if self.config_file and self.config_file.exists():
            try:
                self.config_file.unlink()
            except Exception:
                pass
            self.config_file = None

    @contextmanager
    def proxy_environment(self):
        """
        Context manager that sets proxy environment variables.

        Usage:
            with manager.proxy_environment():
                # HTTP_PROXY and HTTPS_PROXY are set
                response = requests.get("https://example.com")
        """
        # Save original env vars
        original_http_proxy = os.environ.get("HTTP_PROXY")
        original_https_proxy = os.environ.get("HTTPS_PROXY")
        original_http_proxy_lower = os.environ.get("http_proxy")
        original_https_proxy_lower = os.environ.get("https_proxy")

        proxy_url = f"http://127.0.0.1:{self.http_port}"

        try:
            # Start xray if configured and not running
            if self.vless_config and not self.is_running():
                self.start()

            # Set proxy env vars if xray is running
            if self.is_running():
                os.environ["HTTP_PROXY"] = proxy_url
                os.environ["HTTPS_PROXY"] = proxy_url
                os.environ["http_proxy"] = proxy_url
                os.environ["https_proxy"] = proxy_url
                logger.debug(f"Proxy environment set: {proxy_url}")

            yield

        finally:
            # Restore original env vars
            if original_http_proxy is not None:
                os.environ["HTTP_PROXY"] = original_http_proxy
            else:
                os.environ.pop("HTTP_PROXY", None)

            if original_https_proxy is not None:
                os.environ["HTTPS_PROXY"] = original_https_proxy
            else:
                os.environ.pop("HTTPS_PROXY", None)

            if original_http_proxy_lower is not None:
                os.environ["http_proxy"] = original_http_proxy_lower
            else:
                os.environ.pop("http_proxy", None)

            if original_https_proxy_lower is not None:
                os.environ["https_proxy"] = original_https_proxy_lower
            else:
                os.environ.pop("https_proxy", None)

    def get_status(self) -> dict:
        """
        Get current proxy status.

        Returns:
            Status dict with running state and configuration
        """
        return {
            "xray_available": self.is_xray_available(),
            "xray_path": self._xray_path,
            "is_running": self.is_running(),
            "socks_port": self.socks_port,
            "http_port": self.http_port,
            "configured": self.vless_config is not None,
            "vless_server": (
                f"{self.vless_config.address}:{self.vless_config.port}"
                if self.vless_config
                else None
            ),
            "vless_security": self.vless_config.security if self.vless_config else None,
        }

    def test_connection(
        self, target_url: str = "https://generativelanguage.googleapis.com"
    ) -> dict:
        """
        Test proxy connection to a target URL.

        Args:
            target_url: URL to test connection to

        Returns:
            Test result dict
        """
        import httpx

        if not self.vless_config:
            return {"success": False, "error": "No VLESS configuration"}

        if not self.start():
            return {"success": False, "error": "Failed to start xray"}

        try:
            with self.proxy_environment():
                # Use httpx with proxy
                proxy_url = f"http://127.0.0.1:{self.http_port}"
                client = httpx.Client(proxy=proxy_url, timeout=10.0)
                response = client.head(target_url)
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "target": target_url,
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def __del__(self):
        """Cleanup on deletion."""
        self.stop()


# Module-level singleton for shared proxy manager
_proxy_manager: Optional[XrayProxyManager] = None


def get_proxy_manager() -> XrayProxyManager:
    """Get or create the singleton proxy manager."""
    global _proxy_manager
    if _proxy_manager is None:
        _proxy_manager = XrayProxyManager()
    return _proxy_manager


def validate_vless_url(vless_url: str) -> tuple[bool, str]:
    """
    Validate a VLESS URL without configuring it.

    Args:
        vless_url: VLESS URL to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not vless_url:
        return False, "Empty URL"

    try:
        config = parse_vless_url(vless_url)
        # Basic validation
        if not config.uuid:
            return False, "Missing UUID"
        if not config.address:
            return False, "Missing server address"
        if not config.port:
            return False, "Missing port"
        if config.security == "reality" and not config.public_key:
            return False, "Reality security requires public key (pbk)"
        return True, ""
    except ValueError as e:
        return False, str(e)
