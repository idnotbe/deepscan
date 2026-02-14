"""DeepScan REPL Executor Module.

Session-scoped subprocess for safe REPL execution with timeout.
P7-001: Prevents DoS attacks via infinite loops or CPU-intensive code.
"""

from __future__ import annotations

__all__ = [
    # Main class
    "SafeREPLExecutor",
    # Factory functions
    "get_repl_executor",
    "reset_global_state",
    # Note: _execute_with_thread_timeout is private (internal use only)
]

import logging
import threading
from multiprocessing import Process, Queue
from queue import Empty
from typing import Any

from cancellation import get_cancellation_manager
from constants import (
    DEFAULT_EXEC_TIMEOUT,
    SAFE_BUILTINS,
)


class SafeREPLExecutor:
    """Session-scoped subprocess for safe REPL execution with timeout.

    P7-001: Prevents DoS attacks via infinite loops or CPU-intensive code.

    Maintains state across commands while providing timeout protection.
    If a command times out, the worker is terminated and restarted.

    Usage:
        executor = SafeREPLExecutor(timeout=5)
        result = executor.execute("x = 42")
        result = executor.execute("print(x)")  # State preserved
        executor.shutdown()
    """

    def __init__(self, timeout: int = DEFAULT_EXEC_TIMEOUT):
        """Initialize executor.

        Args:
            timeout: Maximum seconds for command execution.
        """
        self.timeout = timeout
        self.worker: Process | None = None
        self.cmd_queue: Queue = Queue()
        self.result_queue: Queue = Queue()
        self._namespace_init = {"__builtins__": SAFE_BUILTINS}
        self._start_worker()

    def _start_worker(self) -> None:
        """Start or restart the worker process."""
        if self.worker and self.worker.is_alive():
            return

        self.worker = Process(
            target=self._worker_loop,
            args=(self.cmd_queue, self.result_queue, self._namespace_init.copy()),
            daemon=True,
        )
        self.worker.start()

    @staticmethod
    def _worker_loop(
        cmd_queue: Queue,
        result_queue: Queue,
        namespace: dict[str, Any],
    ) -> None:
        """Worker process main loop.

        P2-FIX: Includes resource limits (Unix only) to prevent DoS.
        Maintains namespace state between commands.
        """
        # P2-FIX: Apply resource limits (Unix only) to prevent memory/CPU DoS
        try:
            import resource

            # Memory limit: 256MB (soft), 512MB (hard)
            resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 512 * 1024 * 1024))
            # CPU time limit: 60 seconds (soft), 120 seconds (hard)
            resource.setrlimit(resource.RLIMIT_CPU, (60, 120))
            # Max file size: 10MB (prevent disk abuse)
            resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 * 1024, 10 * 1024 * 1024))
        except (ImportError, ValueError, OSError):
            # resource module not available (Windows) or limits not supported
            pass

        while True:
            try:
                code = cmd_queue.get()
            except (EOFError, KeyboardInterrupt):
                break

            if code is None:  # Shutdown signal
                break

            try:
                # Try eval first (expressions)
                result = eval(code, namespace)
                result_queue.put(("eval_ok", result))
            except SyntaxError:
                # Fall back to exec (statements)
                try:
                    exec(code, namespace)
                    result_queue.put(("exec_ok", None))
                except Exception as e:
                    result_queue.put(("error", f"{type(e).__name__}: {e}"))
            except Exception as e:
                result_queue.put(("error", f"{type(e).__name__}: {e}"))

    def execute(self, code: str) -> Any:
        """Execute code with timeout protection.

        Args:
            code: Python code to execute.

        Returns:
            Result of eval() if expression, None if statement.

        Raises:
            TimeoutError: If execution exceeds timeout.
            RuntimeError: If code raises an exception.
        """
        self._start_worker()  # Ensure worker is alive
        self.cmd_queue.put(code)

        try:
            status, result = self.result_queue.get(timeout=self.timeout)
        except Empty as err:
            # Timeout - terminate and restart worker
            self._terminate_worker()
            raise TimeoutError(
                f"Execution timed out after {self.timeout}s. Worker terminated and restarted."
            ) from err

        if status == "error":
            raise RuntimeError(result)

        return result

    def _terminate_worker(self) -> None:
        """Forcibly terminate the worker process."""
        if not self.worker:
            return

        self.worker.terminate()
        self.worker.join(timeout=1)

        if self.worker.is_alive():
            self.worker.kill()
            self.worker.join(timeout=1)

        self.worker = None
        self._start_worker()  # Fresh worker for next command

    def shutdown(self) -> None:
        """Gracefully shutdown the worker."""
        if self.worker and self.worker.is_alive():
            self.cmd_queue.put(None)  # Shutdown signal
            self.worker.join(timeout=2)
            if self.worker.is_alive():
                self._terminate_worker()
        self.worker = None

    def __del__(self):
        """Cleanup on garbage collection."""
        self.shutdown()


# Global executor instance (lazy initialization)
_repl_executor: SafeREPLExecutor | None = None
_repl_lock = threading.Lock()  # GLOBAL_STATE_FIX: Thread-safe singleton


def get_repl_executor(
    timeout: int = DEFAULT_EXEC_TIMEOUT,
    reset: bool = False,
) -> SafeREPLExecutor:
    """Get or create the global REPL executor.

    Args:
        timeout: Maximum execution time in seconds.
        reset: If True, shutdown existing executor and create new one.
               Use for test isolation.

    Returns:
        The global SafeREPLExecutor instance.

    Note:
        GLOBAL_STATE_FIX: Thread-safe singleton with reset support for testing.
    """
    global _repl_executor

    with _repl_lock:
        if reset and _repl_executor is not None:
            _repl_executor.shutdown()
            _repl_executor = None

        if _repl_executor is None:
            _repl_executor = SafeREPLExecutor(timeout=timeout)

    return _repl_executor


def reset_global_state() -> None:
    """Reset all global mutable state for test isolation.

    GLOBAL_STATE_FIX: Call this in test teardown to prevent state leakage
    between tests. Resets:
    - REPL executor
    - Cancellation manager (via get_cancellation_manager with reset=True)

    Example:
        @pytest.fixture(autouse=True)
        def cleanup():
            yield
            reset_global_state()
    """
    global _repl_executor

    # Reset REPL executor
    with _repl_lock:
        if _repl_executor is not None:
            _repl_executor.shutdown()
            _repl_executor = None

    # Reset cancellation manager
    get_cancellation_manager(reset=True)


def _execute_with_thread_timeout(
    code: str,
    namespace: dict[str, Any],
    timeout: int = DEFAULT_EXEC_TIMEOUT,
) -> tuple[str, Any]:
    """Execute code in main process with thread-based timeout.

    P2-FIX: For helper execution path that can't use subprocess (needs StateManager closure).
    Uses a daemon thread with timeout monitoring.

    ZOMBIE_THREAD_WARNING:
    Python threads cannot be forcibly killed. If the code contains an infinite loop
    (e.g., `while True: pass`), the thread will continue running in the background
    after timeout, consuming CPU and holding the GIL until process exit.

    This is a known Python limitation. Mitigations:
    1. Code is AST-validated before execution (no FunctionDef/ClassDef/loops allowed
       in some modes)
    2. SafeREPLExecutor (subprocess) is used when helpers aren't needed
    3. daemon=True ensures the thread won't block process exit

    For truly untrusted code, always use SafeREPLExecutor (subprocess) which can
    be terminated via Process.terminate().

    Args:
        code: Python code to execute.
        namespace: Namespace for execution.
        timeout: Maximum execution time in seconds.

    Returns:
        Tuple of (status, result) where status is "eval_ok", "exec_ok", or "error".
    """
    result_container: dict[str, Any] = {"status": None, "result": None}
    exception_container: list[Exception] = []

    def _execute_in_thread():
        try:
            # Try eval first (expressions)
            result_container["result"] = eval(code, namespace)
            result_container["status"] = "eval_ok"
        except SyntaxError:
            # Fall back to exec (statements)
            try:
                exec(code, namespace)
                result_container["status"] = "exec_ok"
                result_container["result"] = None
            except Exception as e:
                exception_container.append(e)
        except Exception as e:
            exception_container.append(e)

    # Run in daemon thread with timeout
    exec_thread = threading.Thread(target=_execute_in_thread, daemon=True)
    exec_thread.start()
    exec_thread.join(timeout=timeout)

    if exec_thread.is_alive():
        # Thread is still running (timeout occurred)
        # ZOMBIE_THREAD_WARNING: This thread may continue running in background!
        # Python cannot forcibly kill threads. daemon=True ensures it won't block
        # process exit, but it will consume CPU until then.
        logging.getLogger(__name__).warning(
            f"ZOMBIE_THREAD: Code execution timed out after {timeout}s. "
            f"Thread may continue running in background until process exit. "
            f"Consider using SafeREPLExecutor (subprocess) for untrusted code."
        )
        return ("error", f"Execution timed out after {timeout}s")

    if exception_container:
        e = exception_container[0]
        return ("error", f"{type(e).__name__}: {e}")

    return (result_container["status"] or "exec_ok", result_container["result"])
