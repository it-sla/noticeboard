"""Email worker entrypoint: `python -m app.workers.email_worker`."""

import logging
import signal
import time

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.services.delivery import run_once
from app.services.mailer import get_mailer

log = logging.getLogger("worker")
_stop = False


def _handle(*_):
    global _stop
    _stop = True


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    signal.signal(signal.SIGTERM, _handle)
    signal.signal(signal.SIGINT, _handle)
    s = get_settings()
    log.info("worker started (email_mode=%s)", s.email_mode)
    while not _stop:
        try:
            with SessionLocal() as db:
                stats = run_once(db, get_mailer())
            if any(stats.values()):
                log.info("cycle %s", stats)
        except Exception:  # noqa: BLE001 - keep the loop alive; error is logged without content
            log.exception("worker cycle failed")
        time.sleep(s.worker_poll_seconds)
    log.info("worker stopped")


if __name__ == "__main__":
    main()
