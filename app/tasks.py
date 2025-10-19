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


def reconcile_has_folder(app, batch_size: int = 50):
    """Scan a limited number of scripts with is_has_folder == False and update the DB
    if their project folder exists on disk. This keeps per-request latency low while
    ensuring eventual consistency.

    Usage: schedule this periodically (cron/worker) or publish a job to JOB_QUEUE.
    """
    from .models.script import Script
    from .extensions import db as _db

    updated = 0
    try:
        with app.app_context():
            # Query a small batch of scripts that are missing the folder flag
            candidates = (
                _db.session.query(Script)
                .filter(Script.is_has_folder == False)
                .limit(batch_size)
                .all()
            )

            from .utils import get_project_path

            for script in candidates:
                try:
                    # Compute project path using utility (avoid expensive imports at module load)
                    project_root = app.root_path.parent
                    project_path = Path(get_project_path(script.script_data, project_root)).resolve()
                    if project_path.exists():
                        script.is_has_folder = True
                        _db.session.add(script)
                        updated += 1
                except Exception:
                    # Ignore per-script errors and continue
                    continue

            if updated > 0:
                try:
                    _db.session.commit()
                    log.info("reconcile.is_has_folder.committed", updated=updated)
                except Exception as e:
                    _db.session.rollback()
                    log.error("reconcile.is_has_folder.commit_failed", error=str(e))
    except Exception as e:
        log.error("reconcile.is_has_folder.failed", error=str(e))


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