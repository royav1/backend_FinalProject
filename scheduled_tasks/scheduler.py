import asyncio
from datetime import timedelta
from django.utils.timezone import now as timezone_now
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from scheduled_tasks.sale_events import sale_events
from asgiref.sync import sync_to_async

scheduler = BackgroundScheduler()

async def async_scraping_wrapper():
    """Runs scraping for the first product of each watchlist based on sale event or 7-day rules."""
    try:
        print("⏳ Running scheduled scraping...")

        from base.models import Watchlist
        from scheduled_tasks.actions import run_scraping

        today = timezone_now().date()

        # Step 1: Check if today is within a sale event
        active_event = None
        for event in sale_events:
            if event["start"].date() <= today <= event["end"].date():
                active_event = event
                break

        print(f"📆 Today: {today} — Sale Event: {active_event['name'] if active_event else 'None'}")

        # Step 2: Load all watchlists where user's scraping is enabled
        watchlists = await sync_to_async(
            lambda: list(
                Watchlist.objects.prefetch_related("products")
                .filter(user__userprofile__scheduled_scraping_enabled=True)
            )
        )()

        products_to_scrape = []

        for watchlist in watchlists:
            has_products = await sync_to_async(watchlist.products.exists)()
            if not has_products:
                continue

            # Only take the first product in the watchlist
            tracked_product = await sync_to_async(watchlist.products.first)()
            if not tracked_product:
                continue

            # Check the product's most recent price history
            latest_history = await sync_to_async(
                lambda: tracked_product.price_history.order_by("-date_recorded").first()
            )()

            if not latest_history:
                # No scrape history — must scrape
                print(f"🆕 Product '{tracked_product.title}' has no price history — adding to scrape.")
                products_to_scrape.append(tracked_product)
                continue

            last_scraped_date = latest_history.date_recorded.date()

            if active_event:
                # If sale event is active, check if last scrape was during it
                if not (active_event["start"].date() <= last_scraped_date <= active_event["end"].date()):
                    print(f"📢 Product '{tracked_product.title}' not scraped during '{active_event['name']}' — adding to scrape.")
                    products_to_scrape.append(tracked_product)
                else:
                    print(f"✅ Product '{tracked_product.title}' already scraped during '{active_event['name']}' — skipping.")
            else:
                # No sale event — check if last scrape was over 7 days ago
                if (today - last_scraped_date) > timedelta(days=7):
                    print(f"📆 Product '{tracked_product.title}' last scraped on {last_scraped_date} — adding to scrape.")
                    products_to_scrape.append(tracked_product)
                else:
                    print(f"✅ Product '{tracked_product.title}' scraped recently ({last_scraped_date}) — skipping.")

        print(f"🧩 Total products to scrape today: {len(products_to_scrape)}")

        if products_to_scrape:
            await run_scraping(
                filtered_products=products_to_scrape,
                event_name=active_event["name"] if active_event else None
            )
        else:
            print("✅ No scraping needed today.")

        print("✅ Scheduled scraping completed.")
    except Exception as e:
        print(f"❌ Error during scheduled scraping: {e}")

def start_scheduler():
    """Starts the daily scraping scheduler at 03:00 AM."""
    try:
        scheduler.add_job(
            lambda: asyncio.run(async_scraping_wrapper()),
            # trigger=CronTrigger(hour=3, minute=0),
            trigger=CronTrigger(hour=20, minute=35),
            id="daily_scheduled_scraping",
            replace_existing=True
        )

        scheduler.start()
        print("✅ Scheduler started. Scraping will run daily at 03:00.")
    except Exception as e:
        print(f"❌ Error starting scheduler: {e}")
