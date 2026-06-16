"""
Entrypoint scheduler: menjalankan supervisor.pipeline.run_supervisor()
secara berkala (default tiap N jam, lihat SCHEDULE_INTERVAL_HOURS di .env).

Cara pakai:
    python scheduler/scheduler.py
Alternatif: jalankan via cron tanpa script ini, panggil langsung
    python -m supervisor.pipeline
"""

import logging
from apscheduler.schedulers.blocking import BlockingScheduler

from config.settings import SCHEDULE_INTERVAL_HOURS
from supervisor.pipeline import run_supervisor

logging.basicConfig(
    level= logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("scheduler")

def main():
    scheduler = BlockingScheduler()
    scheduler.add_job(
        run_supervisor,
        trigger="cron",
        hour=0,
        minute=0,
        second=0,
        timezone="Asia/Jakarta",
        id="rag_supervisor_job",
    )
    
    logger.info("Scheduler dimulai. Supervisor akan berjalan setiap %d jam.",SCHEDULE_INTERVAL_HOURS)
    
    run_supervisor()
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler dihentikan.")


if __name__ == "__main__":
    main()
