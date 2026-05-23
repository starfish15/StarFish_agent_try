from datetime import datetime, timezone

from tools.base import BaseTool


class CurrentTimeTool(BaseTool):
    @property
    def name(self) -> str:
        return "get_current_time"

    @property
    def description(self) -> str:
        return (
            "Get the current local time. "
            "Params: format (optional: iso|timestamp|readable|date)."
        )

    def run(self, format: str = "iso") -> dict:
        fmt = "iso"
        if format is not None:
            fmt = str(format).strip().lower() or "iso"
        now = datetime.now().astimezone()
        utc_now = now.astimezone(timezone.utc)

        if fmt == "timestamp":
            return {
                "timestamp": now.timestamp(),
                "utc_timestamp": utc_now.timestamp(),
                "timezone": str(now.tzinfo),
            }
        if fmt == "readable":
            return {
                "time": now.strftime("%Y-%m-%d %H:%M:%S"),
                "utc_time": utc_now.strftime("%Y-%m-%d %H:%M:%S"),
                "timezone": str(now.tzinfo),
            }
        if fmt == "date":
            return {
                "date": f"{now.year}/{now.month}/{now.day}",
                "utc_date": f"{utc_now.year}/{utc_now.month}/{utc_now.day}",
                "timezone": str(now.tzinfo),
            }
        if fmt != "iso":
            return {
                "error": "Unsupported format. Use iso, timestamp, readable, or date.",
                "supported": ["iso", "timestamp", "readable", "date"],
            }

        return {
            "iso": now.isoformat(),
            "utc_iso": utc_now.isoformat(),
            "timezone": str(now.tzinfo),
        }
