import queue
import threading
import json
import redis
from datetime import datetime, timezone
from pathlib import Path
import contextlib
import structlog

# These are initialized by init_tasks
redis_client = None
JOB_QUEUE = queue.Queue()
BACKGROUND_JOBS = {}
REDIS_CHANNEL = 'job_updates'

# module logger
log = structlog.get_logger()

def job_worker(app):
    """A dedicated worker thread that processes jobs from the JOB_QUEUE one by one."""
    while True:
        try:
            job = JOB_QUEUE.get()  # This will block until a job is available
            target_func = job.get('target')
            args = job.get('args', ())
            if callable(target_func):
                with app.app_context():
                    target_func(*args)
        except Exception as e:
            # Use app logger if available, otherwise print
            if app:
                app.logger.exception("Error in job worker thread.")
            else:
                print(f"Error in job worker thread: {e}")

def init_tasks(app):
    """Initializes the task runner background thread and Redis client."""
    global redis_client
    redis_client = redis.Redis(
        host=app.config.get('REDIS_HOST', 'localhost'),
        port=app.config.get('REDIS_PORT', 6379),
        db=app.config.get('REDIS_DB', 0),
        decode_responses=True
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

    # Start the single job worker thread
    threading.Thread(target=job_worker, args=(app,), daemon=True).start()
    log.info("Job worker thread started.")