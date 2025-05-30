from django.core.management.base import BaseCommand
from base.models import TrackedProduct, PriceHistory
from django.utils import timezone
from decimal import Decimal, InvalidOperation


class Command(BaseCommand):
    help = "Test the target price drop alert logic."

    def handle(self, *args, **options):
        def check_target_price_drop(product, current_price):
            """
            Check if the current price dropped below the target price.
            Also shows price drop percentage since previous entry.
            """
            if current_price is None:
                print(f"❌ Invalid current price for '{product.title}'.")
                return False

            if product.target_price is None:
                print(f"⚠️ No target price set for '{product.title}'. Skipping test.")
                return False

            try:
                target_price = Decimal(str(product.target_price))
                current_price = Decimal(str(current_price))

                # Optional: Show price drop since last record
                previous_entry = product.price_history.order_by('-date_recorded').first()
                if previous_entry and previous_entry.price_numeric:
                    previous_price = Decimal(str(previous_entry.price_numeric))
                    drop_percent = ((previous_price - current_price) / previous_price) * 100
                    print(f"📉 Price dropped {drop_percent:.2f}% since last record (from ${previous_price:.2f} to ${current_price:.2f})")
                else:
                    print("ℹ️ No valid previous price history found.")

                # Compare against target price
                if current_price < target_price:
                    print(f"✅ Current price (${current_price:.2f}) is below target price (${target_price:.2f})")
                    return True
                else:
                    print(f"❌ Current price (${current_price:.2f}) is above or equal to target price (${target_price:.2f})")
                    return False

            except InvalidOperation:
                print(f"❌ Error comparing prices for '{product.title}'. Ensure numeric values are valid.")
                return False

        # Step 1: Create test product
        product = TrackedProduct.objects.create(
            user_id=1,  # Replace with a valid user ID
            title="Test Product for Target Price",
            price=Decimal("100.00"),
            target_price=Decimal("80.00"),
            rating=4.5,
            reviews=150,
            availability="In Stock",
            date_scraped=timezone.now()
        )
        self.stdout.write(f"🛒 Created test product: {product.title} with target price ${product.target_price}")

        # Step 2: Add initial price history
        PriceHistory.objects.create(
            product=product,
            price=Decimal("100.00"),
            price_numeric=Decimal("100.00"),
            availability="In Stock",
            date_recorded=timezone.now()
        )
        self.stdout.write("🕒 Added baseline price history at $100.00")

        # Step 3: Test where price is ABOVE the target
        test_price_1 = Decimal("85.00")
        self.stdout.write(f"\n🔎 Case 1: Testing with price = ${test_price_1}")
        if check_target_price_drop(product, test_price_1):
            self.stdout.write("🚨 ALERT: Price below target!\n")
        else:
            self.stdout.write("✅ NO ALERT: Price is still above target.\n")

        # Step 4: Test where price is BELOW the target
        test_price_2 = Decimal("75.00")
        self.stdout.write(f"\n🔎 Case 2: Testing with price = ${test_price_2}")
        if check_target_price_drop(product, test_price_2):
            self.stdout.write("🚨 ALERT: Price below target!\n")
        else:
            self.stdout.write("✅ NO ALERT: Price is still above target.\n")

        # Step 5: Clean up test product
        product.delete()
        self.stdout.write("🧹 Test product deleted.")
