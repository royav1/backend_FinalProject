import asyncio
from django.core.management.base import BaseCommand
from scraper.refinement_scraper import scrape_hardcoded_product  # Ensure correct import path
import logging

# Configure logging for the command
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Test hard-coded scraping functionality with a single product."

    def handle(self, *args, **options):
        """
        Entry point for the management command to run the hard-coded scraping test.
        """
        try:
            self.stdout.write("Starting hard-coded scraping test...")
            asyncio.run(self.run_scraping_test())
            self.stdout.write("Hard-coded scraping test completed successfully.")
        except Exception as e:
            error_message = f"Error during hard-coded scraping test: {e}"
            self.stderr.write(error_message)
            logger.error(error_message, exc_info=True)

    async def run_scraping_test(self):
        """
        Wrapper to run the hard-coded scraping function and handle errors.
        """
        try:
            await scrape_hardcoded_product()
        except Exception as e:
            error_message = f"Error while running hard-coded scraping test: {e}"
            self.stderr.write(error_message)
            logger.error(error_message, exc_info=True)
