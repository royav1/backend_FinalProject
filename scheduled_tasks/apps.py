# scheduled_tasks/apps.py

from django.apps import AppConfig
import os
import atexit
from scheduled_tasks.scheduler import start_scheduler, scheduler


# This file ensures that:
# 1. The scheduler starts once when the Django app loads.
# 2. It registers all scraping jobs (like daily at 03:00).
# 3. It avoids running twice in dev.
# 4. It shuts down cleanly when Django stops.
# This is critical for:
# 1. Running automated daily scraping consistently.
# 2. Making sure the scraping logic (in actions.py) runs automatically, not just manually.

class ScheduledTasksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'scheduled_tasks'

    def ready(self):
        """Starts the APScheduler and registers jobs — only once."""
        # ✅ Avoid running this multiple times in Django dev server
        if os.environ.get("RUN_MAIN") != "true":
            return

        if scheduler.state != 1:
            print("✅ Starting APScheduler from ScheduledTasksConfig...")

            try:
                start_scheduler()
                print("✅ Scheduler started and jobs registered.")
            except Exception as e:
                print(f"❌ Failed to schedule job: {e}")

            # ✅ Ensure scheduler shuts down gracefully when the app exits
            atexit.register(lambda: scheduler.shutdown(wait=False))
