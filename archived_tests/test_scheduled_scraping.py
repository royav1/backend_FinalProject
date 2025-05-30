# from django.core.management.base import BaseCommand
# from base.models import Watchlist, TrackedProduct, PriceHistory
# from scheduled_tasks.actions import process_watchlist_scraping
# import time
# import logging

# # Configure logging for the command
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# class Command(BaseCommand):
#     help = "Test the scheduled scraping functionality."

#     def handle(self, *args, **options):
#         user_id = 3  # User ID for "baga"
#         self.stdout.write(f"Testing scheduled scraping for user with ID {user_id}...")

#         try:
#             # Step 1: Fetch user-specific watchlists and products
#             watchlists = Watchlist.objects.filter(user_id=user_id).prefetch_related("products")
#             if not watchlists.exists():
#                 self.stdout.write(f"No watchlists found for user with ID {user_id}.")
#                 return

#             self.stdout.write(f"User with ID {user_id} has {watchlists.count()} watchlists.")

#             # Print watchlist details for debugging
#             for watchlist in watchlists:
#                 self.stdout.write(f"Watchlist: {watchlist.name} ({watchlist.products.count()} products)")
#                 for product in watchlist.products.all():
#                     last_scraped = product.date_scraped or "Never scraped"
#                     self.stdout.write(f"  - Product: {product.title}, Last Scraped: {last_scraped}")

#             # Step 2: Trigger the watchlist scraping task
#             self.stdout.write("Starting watchlist scraping...")
#             logger.info("Triggering the Celery task: process_watchlist_scraping.")
#             process_watchlist_scraping.delay()  # Use .delay() to run the Celery task asynchronously

#             # Allow some time for the scraping task to run
#             delay_seconds = 20  # Adjust the delay for task completion
#             self.stdout.write(f"Waiting {delay_seconds} seconds for scraping to complete...")
#             time.sleep(delay_seconds)

#             # Step 3: Verify the results
#             self.stdout.write("Watchlist scraping completed. Verifying results...")
#             logger.info("Verifying results of the watchlist scraping.")

#             for watchlist in watchlists:
#                 self.stdout.write(f"Results for watchlist: {watchlist.name}")
#                 for product in watchlist.products.all():
#                     # Fetch the updated product instance
#                     updated_product = TrackedProduct.objects.get(id=product.id)

#                     price_history = (
#                         PriceHistory.objects.filter(product=updated_product)
#                         .order_by("-date_recorded")
#                         .first()
#                     )

#                     self.stdout.write(f"  - Product: {updated_product.title}")
#                     last_scraped = updated_product.date_scraped or "Never scraped"
#                     self.stdout.write(f"    Last Scraped: {last_scraped}")
#                     if price_history:
#                         self.stdout.write(f"    Latest Price: {price_history.price_numeric}")
#                         self.stdout.write(f"    Availability: {price_history.availability}")
#                     else:
#                         self.stdout.write(f"    No price history available.")
#                     logger.info(
#                         f"Verified product '{updated_product.title}' - Last Scraped: {last_scraped}, "
#                         f"Latest Price: {price_history.price_numeric if price_history else 'N/A'}, "
#                         f"Availability: {price_history.availability if price_history else 'N/A'}"
#                     )

#         except Exception as e:
#             error_message = f"Error during test: {e}"
#             self.stderr.write(error_message)
#             logger.error(error_message, exc_info=True)
