"""Protocol interface for Android device communication."""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class AndroidDeviceProtocol(Protocol):
    """Protocol defining the interface for Android device backends.

    Any class implementing these methods and attributes can serve as a
    device backend for the MCP server components (UILayoutExtractor,
    ScreenInteractor, MediaCapture, LogMonitor, etc.).

    This enables cleaner mocking in tests, reduces coupling to the
    concrete ADBManager, and allows future alternative backends
    (e.g. wireless ADB, emulator-specific APIs).
    """

    selected_device: Optional[str]

    def default_device_id(self) -> str:
        """Return the current default device id or raise if none selected."""
        ...

    async def execute_adb_command(
        self,
        command: str,
        *,
        device_id: Optional[str],
        timeout: int = 30,
        capture_output: bool = True,
        check_device: bool = True,
    ) -> Dict[str, Any]:
        """Execute a device command with error handling and timeout.

        ``device_id`` is keyword-only and required; pass ``None`` only for
        device-agnostic commands like ``adb devices``.
        """
        ...

    async def spawn_adb_process(
        self,
        cmd_template: str,
        *,
        device_id: str,
        stdout: Optional[int] = None,
        stderr: Optional[int] = None,
        stdin: Optional[int] = None,
    ) -> Any:
        """Spawn a long-running adb process. Caller owns the lifecycle."""
        ...

    async def list_devices(self) -> List[Dict[str, Any]]:
        """List all connected devices."""
        ...

    async def auto_select_device(self) -> Dict[str, Any]:
        """Auto-select best available device."""
        ...

    async def get_device_info(
        self, device_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get detailed device information."""
        ...

    async def get_screen_size(
        self, device_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get device screen dimensions."""
        ...

    async def check_device_health(
        self, device_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check if device is responsive and ready."""
        ...

    async def get_foreground_app(
        self, device_id: Optional[str] = None, timeout: int = 5
    ) -> Dict[str, Any]:
        """Detect the currently foreground app."""
        ...
