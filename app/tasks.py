import queue
import threading
import redis
from pathlib import Path
import structlog
import os

# These are initialized by init_tasks
redis_client = None
JOB_QUEUE = queue.Queue()
BACKGROUND_JOBS = {}
REDIS_CHANNEL = 'job_updates'
DEFAULT_NUM_WORKERS = 4
NUM_WORKERS = DEFAULT_NUM_WORKERS

# module logger
log = structlog.get_logger()


# Event used to signal workers to stop (best-effort). Threads still start as
# daemon threads by default to avoid preventing process exit in simple setups.
STOP_EVENT = threading.Event()


def _parse_workers(raw_value, default=DEFAULT_NUM_WORKERS, min_v=1, max_v=32):
    """Parse and clamp a raw worker value from config/env.

    Returns an int in range [min_v, max_v]. Logs a warning when input is invalid
    or out of range and falls back to default.
    """
    try:
        v = int(raw_value)
    except Exception:
        log.warning("NUM_WORKERS invalid, using default", raw_value=raw_value, default=default)
        return default

    if v < min_v or v > max_v:
        log.warning("NUM_WORKERS out of allowed range, clamping", raw_value=v, min=min_v, max=max_v)
    return max(min(v, max_v), min_v)

def job_worker(app):
    """A dedicated worker thread that processes jobs from the JOB_QUEUE one by one."""
    while not STOP_EVENT.is_set():
        try:
            # use a short timeout to allow checking STOP_EVENT periodically
            job = JOB_QUEUE.get(timeout=1)
        except queue.Empty:
            continue

        try:
            target_func = job.get('target')
            args = job.get('args', ())
            if callable(target_func):
                with app.app_context():
                    target_func(*args)
        except Exception as e:
            # Use app logger if available, otherwise print
            if app:
                try:
                    app.logger.exception("Error in job worker thread.")
                except Exception:
                    log.exception("Error in job worker thread")
            else:
                print(f"Error in job worker thread: {e}")
        finally:
            try:
                JOB_QUEUE.task_done()
            except Exception:
                pass

def init_tasks(app):
    """Initializes the task runner background thread and Redis client."""
    global redis_client, BACKGROUND_JOBS

    # Determine worker count from app config -> env var -> default and validate
    raw = app.config.get('NUM_WORKERS', None)
    if raw is None:
        raw = os.getenv('NUM_WORKERS', DEFAULT_NUM_WORKERS)

    num_workers = _parse_workers(raw, default=DEFAULT_NUM_WORKERS)

    # update alias for backward compatibility
    global NUM_WORKERS
    NUM_WORKERS = num_workers

    log.info(f"Starting {num_workers} job worker threads.")

    redis_client = redis.Redis(
        host=app.config.get('REDIS_HOST', 'localhost'),
        port=app.config.get('REDIS_PORT', 6379),
        db=app.config.get('REDIS_DB', 0),
        decode_responses=True,
    )
    try:
        redis_client.ping() # Check connection
        log.info("Redis connection successful.")
    except redis.exceptions.ConnectionError as e:
        # Log via structlog and also keep app logger for backwards compatibility
        log.error("Redis connection failed", error=str(e))
        try:
            app.logger.error(f"Redis connection failed: {e}")
        except Exception:
            pass
        # Also print a prominent red message to stderr so it's visible in consoles
        try:
            # ANSI red text; many terminals will render this in red
            red = "\x1b[31m"
            reset = "\x1b[0m"
            msg = f"{red}ERROR: Redis connection failed (localhost:6379). Some background features will be disabled.\n  Details: {e}{reset}"
            import sys
            print(msg, file=sys.stderr)
        except Exception:
            # Fallback plain message
            try:
                import sys
                print("ERROR: Redis connection failed (localhost:6379). Some background features will be disabled.", file=sys.stderr)
            except Exception:
                pass


    for i in range(num_workers):
        thread_name = f"Worker-Thread-{i+1}"
        thread = threading.Thread(
            target=job_worker,
            args=(app,),
            daemon=True,
            name=thread_name,  # Gán tên để dễ debug
        )
        thread.start()
        # store actual thread object for runtime introspection
        try:
            BACKGROUND_JOBS[thread_name] = thread
        except Exception:
            # best-effort bookkeeping
            pass

    log.info(f"{num_workers} job worker threads started.")