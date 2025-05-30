from django.core.management.base import BaseCommand
from base.models import TrackedProduct, PriceHistory
from django.utils import timezone
from decimal import Decimal, InvalidOperation


class Command(BaseCommand):
    help = "Test the price drop detection logic."

    def handle(self, *args, **options):
        # Step 1: Define detect_price_drop function
        def detect_price_drop(product, current_price, threshold=30):
            """
            Detect if there is a price drop equal to or greater than the given threshold percentage.
            """
            if not current_price or current_price <= 0:
                print(f"Invalid current price for product '{product.title}': {current_price}")
                return False

            # Fetch the most recent price history
            previous_price_entry = product.price_history.order_by('-date_recorded').first()

            if not previous_price_entry:
                print(f"No previous price history for product '{product.title}'. Cannot detect price drop.")
                return False

            if not previous_price_entry.price_numeric or previous_price_entry.price_numeric <= 0:
                print(f"Invalid previous price in history for product '{product.title}': {previous_price_entry.price_numeric}")
                return False

            try:
                # Ensure both prices are Decimal for arithmetic operations
                previous_price = Decimal(str(previous_price_entry.price_numeric))

                # Calculate price drop percentage
                price_drop_percentage = ((previous_price - current_price) / previous_price) * 100

                if price_drop_percentage >= threshold:
                    print(f"Significant price drop detected for '{product.title}': {price_drop_percentage:.2f}%")
                    return True  # Significant price drop detected
                else:
                    print(f"No significant price drop for '{product.title}': {price_drop_percentage:.2f}%")
                    return False

            except InvalidOperation:
                print(f"Error calculating price drop for '{product.title}'. Ensure numeric consistency.")
                return False

        # Step 2: Add a Test Product
        product = TrackedProduct.objects.create(
            user_id=1,  # Replace with an existing user ID
            title="Test Product for Price Drop",
            price="100.00",  # Initial regular price as a numeric-compatible string
            rating=4.5,
            reviews=150,
            availability="In Stock",
            date_scraped=timezone.now()
        )
        self.stdout.write(f"Created product: {product.title}")

        # Step 3: Add Price History
        PriceHistory.objects.create(
            product=product,
            price="100.00",  # Previous price as string
            price_numeric=100.00,  # Numeric version of the price
            availability="In Stock",
            date_recorded=timezone.now()
        )
        self.stdout.write("Added initial price history.")

        # Step 4: Test Price Drop Detection with a threshold
        try:
            new_price = Decimal('65.00')  # Simulate a new price drop
        except InvalidOperation:
            self.stdout.write("Invalid new price format. Ensure valid numeric input.")
            return

        threshold = 30  # Threshold percentage for detection

        # Call the function and check for price drop
        is_price_drop = detect_price_drop(product, new_price, threshold=threshold)

        if is_price_drop:
            self.stdout.write(f"✅ ALERT: Significant price drop detected (threshold = {threshold}%)!")
        else:
            self.stdout.write(f"❌ No significant price drop detected (threshold = {threshold}%).")

        # Step 5: Clean Up
        product.delete()
        self.stdout.write("Test product deleted.")
