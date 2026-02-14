"""Work Cancellation Manager for DeepScan (Phase 6).

Provides graceful cancellation with "Double Tap" pattern:
- First Ctrl+C: Finish current work, save checkpoint
- Second Ctrl+C: Force quit immediately

Design based on:
- DEEPSCAN_PHASE6_CANCELLATION.md specification
- vibe_check feedback (Rich UI coordination)
- pal/Gemini analysis (signal handler re-entrancy safety)

Key Design Decisions:
1. Use sys.stderr.write() in signal handler (not Rich - re-entrancy safe)
2. Exit code 130 (128 + SIGINT Unix convention)
3. on_cleanup callback for Rich UI coordination
4. Second Ctrl+C always triggers force quit (no timing threshold)
5. Graceful timeout (10s default) with os._exit()
6. mark_completed() must be called after graceful shutdown to prevent timeout

Usage:
    cancel_mgr = CancellationManager(
        on_graceful=lambda: print("Saving checkpoint..."),
        on_cleanup=progress_bar.stop,  # Release Rich UI
    )
    cancel_mgr.setup()

    while processing:
        if cancel_mgr.is_cancelled():
            break
        # ... do work ...

    if cancel_mgr.is_cancelled():
        save_checkpoint()
        cancel_mgr.mark_completed()  # IMPORTANT: Prevent timeout force quit
        cancel_mgr.show_resume_instructions(session_hash)
"""

from __future__ import annotations

__all__ = [
    # Exceptions
    "CancellationError",
    # Main class
    "CancellationManager",
    # Factory functions
    "get_cancellation_manager",
    "atomic_write_with_cancellation",
]

import logging
import os
import signal
import sys
import threading
import time
from collections.abc import Callable

logger = logging.getLogger(__name__)


class CancellationError(Exception):
    """Raised when operation is cancelled by user."""

    def __init__(self, message: str = "Operation cancelled by user"):
        super().__init__(message)


class CancellationManager:
    """Manages graceful cancellation with Double Tap support.

    Thread-safe cancellation manager that handles SIGINT (Ctrl+C) signals
    for graceful shutdown with force quit on second Ctrl+C.

    Behavior:
    - First Ctrl+C: Sets graceful cancellation flag, starts timeout thread
    - Second Ctrl+C: Immediately force quits with exit code 130
    - Timeout: Force quits if graceful shutdown takes too long

    Attributes:
        graceful_timeout: Seconds before auto-force quit after graceful request.

    Example:
        >>> mgr = CancellationManager(graceful_timeout=10.0)
        >>> mgr.setup()
        >>> while not mgr.is_cancelled():
        ...     do_work()
        >>> if mgr.is_cancelled():
        ...     cleanup_and_exit()
    """

    # Exit code constants
    EXIT_CODE_FORCE_QUIT = 130  # 128 + SIGINT (2)

    def __init__(
        self,
        graceful_timeout: float = 10.0,
        on_graceful: Callable[[], None] | None = None,
        on_force: Callable[[], None] | None = None,
        on_cleanup: Callable[[], None] | None = None,
    ):
        """Initialize cancellation manager.

        Args:
            graceful_timeout: Seconds before auto-force quit after first Ctrl+C.
            on_graceful: Callback when graceful shutdown starts (e.g., save checkpoint).
            on_force: Callback when force quit triggered (before os._exit).
            on_cleanup: Callback to release UI resources (called FIRST, before messages).
                       Use this to stop Rich progress bars before printing.
        """
        self._cancel_event = threading.Event()
        self._force_event = threading.Event()
        self._completed_event = threading.Event()

        # Issue AD Fix: Validate graceful_timeout
        if graceful_timeout <= 0:
            raise ValueError(f"graceful_timeout must be positive, got {graceful_timeout}")
        self.graceful_timeout = graceful_timeout

        self._on_graceful = on_graceful
        self._on_force = on_force
        self._on_cleanup = on_cleanup

        self._cancel_count = 0
        self._last_signal_time: float | None = None
        self._graceful_start_time: float | None = None
        self._lock = threading.Lock()

        self._timeout_thread: threading.Thread | None = None

    def setup(self) -> None:
        """Set up signal handlers.

        Platform-specific handling:
        - SIGINT (Ctrl+C): All platforms
        - SIGTERM: Unix/Linux/macOS only (not available on Windows)

        Should be called once at program start, before any interruptible work.
        """
        signal.signal(signal.SIGINT, self._handle_signal)

        # SIGTERM only on Unix-like systems (Issue E Fix)
        # Windows doesn't support SIGTERM via signal.signal()
        if sys.platform != "win32":
            signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum: int, frame) -> None:
        """Handle interrupt signal.

        First signal: Set graceful flag, start timeout thread
        Second signal: Force quit immediately

        Uses sys.stderr.write() instead of print()/Rich to avoid
        re-entrancy issues with terminal output (Gemini recommendation).

        DEADLOCK FIX: Callbacks are executed in a separate thread to prevent
        deadlock when callbacks need locks that might be held by main thread.
        Signal handlers should only set flags and perform minimal re-entrant operations.
        """
        now = time.time()

        with self._lock:
            self._cancel_count += 1

            if self._cancel_count == 1:
                # First Ctrl+C: Graceful shutdown
                self._graceful_start_time = now
                self._last_signal_time = now
                self._cancel_event.set()

                # Output message using sys.stderr.write (re-entrancy safe)
                sys.stderr.write("\n[!] Cancellation requested. Finishing current work...\n")
                sys.stderr.write("    (Press Ctrl+C again to force quit)\n")
                sys.stderr.flush()

                # DEADLOCK FIX: Execute callbacks in separate thread
                # This prevents deadlock if callbacks need locks held by main thread
                # (e.g., Rich's Progress.stop() needs internal locks)
                threading.Thread(
                    target=self._execute_graceful_callbacks,
                    daemon=True,
                    name="CancellationCallbacks",
                ).start()

                # Start timeout thread
                self._timeout_thread = threading.Thread(
                    target=self._graceful_timeout_thread,
                    daemon=True,
                    name="CancellationTimeout",
                )
                self._timeout_thread.start()

            else:
                # Second+ Ctrl+C: Force quit
                self._force_event.set()

                sys.stderr.write("\n[!] Force quitting...\n")
                sys.stderr.write("    Warning: Progress may not be fully saved\n")
                sys.stderr.flush()

                # DEADLOCK FIX: Execute force callback in separate thread
                # Give it a brief moment to complete before force exit
                if self._on_force:
                    callback_thread = threading.Thread(
                        target=self._safe_callback,
                        args=(self._on_force, "Force"),
                        daemon=True,
                        name="ForceCallback",
                    )
                    callback_thread.start()
                    callback_thread.join(timeout=0.5)  # Brief wait for callback

                # Force exit with proper cleanup (Issue M Fix)
                self._force_exit()

    def _execute_graceful_callbacks(self) -> None:
        """Execute graceful shutdown callbacks outside signal handler.

        DEADLOCK FIX: This runs in a separate thread to avoid holding
        signal handler context while executing potentially blocking callbacks.
        """
        # Call cleanup callback FIRST to release Rich UI
        self._safe_callback(self._on_cleanup, "Cleanup")
        # Call graceful callback
        self._safe_callback(self._on_graceful, "Graceful")

    def _safe_callback(
        self, callback: Callable[[], None] | None, name: str
    ) -> None:
        """Safely execute a callback with exception handling.

        Args:
            callback: The callback function to execute.
            name: Name of the callback for logging.
        """
        if callback:
            try:
                callback()
            except Exception as e:
                logger.warning(f"{name} callback failed: {e}")

    def _graceful_timeout_thread(self) -> None:
        """Thread that forces quit after graceful timeout.

        IMPORTANT (Issue F Fix): Uses os._exit() instead of sys.exit() because:
        - sys.exit() only raises SystemExit in the current thread
        - In a daemon thread, this does NOT terminate the main process
        - os._exit() immediately terminates the entire process

        This ensures the timeout actually works when the main thread
        is blocked on I/O operations.
        """
        time.sleep(self.graceful_timeout)

        with self._lock:
            # Check if still in graceful mode (not completed, not already force)
            if (
                self._cancel_event.is_set()
                and not self._force_event.is_set()
                and not self._completed_event.is_set()
            ):
                sys.stderr.write(
                    f"\n[!] Graceful shutdown timed out after {self.graceful_timeout}s\n"
                )
                sys.stderr.write("    Force quitting...\n")
                sys.stderr.flush()

                self._force_event.set()
                self._force_exit()

    def _force_exit(self) -> None:
        """Force exit the process with proper cleanup.

        Issue M Fix: Flush stdout/stderr before os._exit() for observability.
        os._exit() doesn't flush buffers - any pending log messages would be lost.
        """
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(self.EXIT_CODE_FORCE_QUIT)

    def is_cancelled(self) -> bool:
        """Check if cancellation was requested.

        Thread-safe check that can be called from any thread.

        Returns:
            True if graceful cancellation was requested, False otherwise.
        """
        return self._cancel_event.is_set()

    def is_force_quit(self) -> bool:
        """Check if force quit was triggered.

        Thread-safe check that can be called from any thread.

        Returns:
            True if force quit was triggered, False otherwise.
        """
        return self._force_event.is_set()

    def check_and_raise(self) -> None:
        """Check cancellation and raise if force quit was triggered.

        Use this in long-running loops to allow force quit to interrupt
        operations that might be blocking.

        Raises:
            CancellationError: If force quit was triggered.
        """
        if self._force_event.is_set():
            raise CancellationError("Force quit triggered")

    def mark_completed(self) -> None:
        """Mark graceful shutdown as completed.

        Call this after saving checkpoint during graceful shutdown
        to prevent the timeout thread from force quitting the process.

        This method MUST be called by external code after graceful
        cancellation handling is complete. Without this call, the
        timeout thread will force-quit the process after graceful_timeout
        seconds, even if the shutdown completed successfully.

        Example:
            if cancel_mgr.is_cancelled():
                save_checkpoint()
                cancel_mgr.mark_completed()  # Prevent timeout force quit
                cancel_mgr.show_resume_instructions(session_hash)
        """
        self._completed_event.set()

    def reset(self) -> None:
        """Reset cancellation state (for testing).

        Warning: This should only be used in tests, not in production code.
        """
        with self._lock:
            self._cancel_event.clear()
            self._force_event.clear()
            self._completed_event.clear()
            self._cancel_count = 0
            self._last_signal_time = None
            self._graceful_start_time = None

    @staticmethod
    def show_resume_instructions(session_hash: str) -> None:
        """Display resume instructions to user.

        Called after graceful shutdown completes to inform user
        how to resume the interrupted session.

        Args:
            session_hash: Unique session identifier for resume command.
        """
        # Use ANSI colors for visibility (simple, no Rich dependency)
        GREEN = "\033[92m"
        CYAN = "\033[96m"
        RESET = "\033[0m"

        print(f"\n{GREEN}Progress saved.{RESET}")
        print(f"Resume with: {CYAN}deepscan --resume {session_hash}{RESET}")


# =============================================================================
# Global Cancellation Manager (Singleton Pattern)
# =============================================================================

_global_cancel_mgr: CancellationManager | None = None
_factory_lock = threading.Lock()  # Issue AC Fix: Thread-safe singleton


def get_cancellation_manager(
    graceful_timeout: float = 10.0,
    on_graceful: Callable[[], None] | None = None,
    on_force: Callable[[], None] | None = None,
    on_cleanup: Callable[[], None] | None = None,
    reset: bool = False,
) -> CancellationManager:
    """Get or create the global cancellation manager.

    Creates a singleton instance of CancellationManager for use across
    the application. The first call initializes the manager with the
    provided parameters; subsequent calls return the same instance.

    Thread-safe: Uses lock to prevent race conditions during initialization
    (Issue AC Fix).

    Args:
        graceful_timeout: Seconds before auto-force quit.
        on_graceful: Callback when graceful shutdown starts.
        on_force: Callback when force quit triggered.
        on_cleanup: Callback to release UI resources.
        reset: If True, create a new instance (for testing only).

    Returns:
        The global CancellationManager instance.
    """
    global _global_cancel_mgr

    # Issue AC Fix: Thread-safe singleton initialization
    with _factory_lock:
        if _global_cancel_mgr is None or reset:
            _global_cancel_mgr = CancellationManager(
                graceful_timeout=graceful_timeout,
                on_graceful=on_graceful,
                on_force=on_force,
                on_cleanup=on_cleanup,
            )
            _global_cancel_mgr.setup()

    return _global_cancel_mgr


# =============================================================================
# Atomic File Operations with Cancellation Support
# =============================================================================


def atomic_write_with_cancellation(
    file_path: str,
    content: str,
    cancel_mgr: CancellationManager | None = None,
    max_retries: int = 3,
    retry_delay: float = 0.1,
) -> bool:
    """Write file atomically with cancellation check and Windows retry.

    Uses temp-file-and-rename pattern for atomicity.
    Includes Windows retry loop for file locking issues (Issue N Fix).
    Checks cancellation flag in retry loop (Gemini recommendation).

    Args:
        file_path: Path to write to.
        content: Content to write.
        cancel_mgr: Optional CancellationManager to check during retries.
        max_retries: Maximum retry attempts for Windows file locking.
        retry_delay: Delay between retries in seconds.

    Returns:
        True if write succeeded, False if cancelled during retry.

    Raises:
        PermissionError: If write fails after all retries.
        CancellationError: If cancelled during retry.
    """
    from pathlib import Path

    target = Path(file_path)
    tmp_file = target.with_suffix(target.suffix + ".tmp")

    # Issue AA Fix: Write to temp file first with proper error handling
    try:
        tmp_file.write_text(content, encoding="utf-8")
    except Exception as e:
        # Clean up temp file if write fails
        try:
            tmp_file.unlink(missing_ok=True)
        except Exception as cleanup_err:
            # Issue AB Fix: Log cleanup failures instead of silent swallowing
            logger.debug(f"Failed to cleanup temp file after write error: {cleanup_err}")
        logger.error(f"Failed to write temp file {tmp_file}: {e}")
        raise

    # Atomic rename with Windows retry (Issue N Fix)
    for attempt in range(max_retries):
        # IMPORTANT: Only abort on Force Quit, not Graceful Cancellation!
        # Graceful cancellation's purpose is to SAVE progress before exiting.
        # Force quit (double tap) means user wants to exit immediately.
        if cancel_mgr and cancel_mgr.is_force_quit():
            # Clean up temp file on force quit
            try:
                tmp_file.unlink(missing_ok=True)
            except Exception as e:
                # Issue AB Fix: Log cleanup failures instead of silent swallowing
                logger.debug(f"Failed to cleanup temp file on force quit: {e}")
            raise CancellationError("Operation force quit by user")

        try:
            os.replace(str(tmp_file), str(target))
            return True

        except PermissionError as e:
            if attempt < max_retries - 1:
                logger.debug(f"File locked during atomic write, retrying in {retry_delay}s: {e}")
                time.sleep(retry_delay)
            else:
                # Clean up temp file before raising
                try:
                    tmp_file.unlink(missing_ok=True)
                except Exception as cleanup_err:
                    # Issue AB Fix: Log cleanup failures instead of silent swallowing
                    logger.debug(f"Failed to cleanup temp file after retries: {cleanup_err}")

                logger.error(f"Failed to save file after {max_retries} attempts: {e}")
                raise

    return True
