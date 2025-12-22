"""
Progress display utilities for s3lync.
"""

import os
import sys
from typing import Any, Callable, Optional, Tuple

from tqdm import tqdm


def chain_callbacks(
    primary_callback: Callable[[int], None],
    secondary_callback: Optional[Callable[[int], None]] = None,
) -> Callable[[int], None]:
    """
    Chain two callback functions together.

    Calls both callbacks in sequence when invoked. Useful for combining
    progress bar updates with custom callbacks.

    Args:
        primary_callback: Primary callback to call
        secondary_callback: Secondary callback to call (optional)

    Returns:
        Combined callback function
    """
    if secondary_callback is None:
        return primary_callback

    def combined_callback(chunk: int) -> None:
        primary_callback(chunk)
        secondary_callback(chunk)

    return combined_callback


class ProgressBar:
    """Display progress bar for file operations."""

    def __init__(
        self,
        total: int,
        desc: str = "",
        mode: Optional[str] = None,
        position: Optional[int] = None,
        leave: Optional[bool] = None,
    ):
        """
        Initialize progress bar.

        Args:
            total: Total size in bytes
            desc: Description to display
            mode: Display mode ("progress", "compact", "disabled", default: "progress")
            position: Progress bar position (optional)
            leave: Leave progress bar after completion (optional)
        """
        # Validate mode
        if mode is not None:
            valid_modes = {"progress", "compact", "disabled"}
            mode_lower = mode.lower()
            if mode_lower not in valid_modes:
                raise ValueError(
                    f"Invalid progress_mode '{mode}'. "
                    f"Must be one of: {', '.join(sorted(valid_modes))}"
                )

        self.total = total
        self.desc = desc

        # Use provided mode or default to "progress"
        self.mode = (mode or "progress").lower()

        self.pbar: Optional[Any] = None
        self._transferred: int = 0  # used for compact one-shot print
        self._position = position
        # Default leave True for progress bars unless explicitly set (sub-bar often False)
        self._leave = True if leave is None else leave

        # Auto-adjust for environments where tqdm does not render cleanly, e.g. PyCharm Run console.
        effective_mode = self.mode
        if self.mode == "progress" and _is_pycharm_console():
            effective_mode = "compact"

        # Modes:
        # - "progress": interactive tqdm progress bar (standard formatting)
        # - "compact": non-interactive; print one line at completion
        if effective_mode != "disabled":
            if effective_mode == "progress" and tqdm:
                # Restore original behavior: standard tqdm bar
                self.pbar = tqdm(
                    total=total,
                    desc=desc,
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    dynamic_ncols=True,
                    position=(self._position if self._position is not None else 0),
                    leave=self._leave,
                )
            # For compact mode, we intentionally do NOT create tqdm bar.
        # Save back the effective mode so update/close follow the right path
        self.mode = effective_mode

    def update(self, n: int = 1) -> None:
        """Update progress bar."""
        if self.pbar:
            self.pbar.update(n)
        elif self.mode == "compact":
            # accumulate bytes for final one-shot print
            self._transferred += n

    def close(self) -> None:
        """Close progress bar."""
        if self.pbar:
            self.pbar.close()
        elif self.mode == "compact":
            # One-shot print at completion
            try:
                transferred = _format_bytes(self._transferred)
                total = _format_bytes(self.total)
                label = self.desc or "transfer"
                print(f"{label}: 100% ({transferred}/{total})")
            except Exception:
                # Fallback minimal print to avoid breaking flow
                print(f"{self.desc or 'transfer'}: done")

    def __enter__(self) -> "ProgressBar":
        """Context manager entry."""
        return self

    def __exit__(
        self, exc_type: object, exc_val: object, exc_tb: object
    ) -> None:
        """Context manager exit."""
        self.close()


def create_progress_callback(
    total: int,
    desc: str = "",
    mode: Optional[str] = None,
    position: Optional[int] = None,
    leave: Optional[bool] = None,
) -> Tuple[ProgressBar, Callable[[int], None]]:
    """
    Create a progress bar and callback function for boto3.

    Args:
        total: Total size in bytes
        desc: Description to display
        mode: Display mode ("progress", "compact", or "disabled")

    Returns:
        Tuple of (ProgressBar, callback_function)
    """
    pbar = ProgressBar(total, desc, mode, position=position, leave=leave)

    def callback(bytes_amount: int) -> None:
        pbar.update(bytes_amount)

    return pbar, callback

    return pbar, callback


def _format_bytes(num: int) -> str:
    """Format bytes to human-readable string using binary multiples (KiB, MiB, ...)."""
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    size = float(num)
    for unit in units:
        if size < 1024.0 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} {units[-1]}"


def _is_pycharm_console() -> bool:
    """Detect PyCharm/JetBrains run console or non-interactive stdout.

    Heuristics:
    - PYCHARM_HOSTED environment variable is set (common in PyCharm run/debug)
    - JETBRAINS_IDE environment variable is set (JetBrains IDEs)
    - Stdout is not a TTY (progress bars often render poorly)
    """
    try:
        if os.getenv("PYCHARM_HOSTED"):
            return True
        if os.getenv("JETBRAINS_IDE"):
            return True
        # When running inside PyCharm's default Run console, isatty is often False
        if hasattr(sys.stdout, "isatty") and not sys.stdout.isatty():
            return True
    except Exception:
        # On any detection error, do not force change
        return False
    return False
