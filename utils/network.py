"""Network utilities: local LAN IP detection and QR code generation for mobile sync."""
from __future__ import annotations

import base64
import io
import socket
from typing import Optional


def get_local_ip() -> str:
    """Return local LAN IP address of this machine."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Does not actually make a network connection, just selects the outbound route
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def get_network_url(port: int = 8501) -> str:
    """Return full URL to access YT Video Downloader from mobile devices on the same Wi-Fi."""
    ip = get_local_ip()
    return f"http://{ip}:{port}"


def generate_qr_code_base64(data: str) -> str:
    """Generate a high-contrast QR code image encoded as a base64 PNG data URI."""
    try:
        import qrcode

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#65D6C4", back_color="#151D31")

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except Exception:
        return ""
