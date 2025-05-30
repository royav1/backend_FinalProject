from django.db import migrations
from decimal import Decimal, InvalidOperation

def populate_price_numeric(apps, schema_editor):
    """
    Populate the price_numeric field in the PriceHistory table with numeric values extracted from price.
    """
    PriceHistory = apps.get_model('base', 'PriceHistory')  # Correct model
    updated_count = 0  # Track successful updates
    skipped_count = 0  # Track invalid price entries
    no_price_count = 0  # Track entries with no price provided

    for entry in PriceHistory.objects.all():
        try:
            # Check if price exists and is not None
            if not entry.price:
                print(f"Skipping entry ID {entry.id}: No price provided.")
                no_price_count += 1
                continue

            # Extract numeric value from price (e.g., "$123.45")
            price_str = entry.price.replace('$', '').replace(',', '').strip()

            # Skip invalid prices
            if not price_str or price_str.lower() in ["no price found", "n/a"]:
                print(f"Skipping entry ID {entry.id}: Invalid price '{entry.price}'")
                skipped_count += 1
                continue

            # Try converting the price string to a Decimal
            price_numeric = Decimal(price_str)
            entry.price_numeric = price_numeric
            entry.save()

            print(f"Updated entry ID {entry.id}: price_numeric = {price_numeric}")
            updated_count += 1

        except (InvalidOperation, ValueError) as e:
            print(f"Error processing entry ID {entry.id} with price '{entry.price}': {e}")
            skipped_count += 1
        except Exception as e:
            print(f"Unexpected error for entry ID {entry.id}: {e}")
            skipped_count += 1

    # Print summary after processing
    print(f"Migration Summary: {updated_count} entries updated, {skipped_count} invalid prices, {no_price_count} with no price field.")

def noop_reverse_code(apps, schema_editor):
    """
    No operation for reverse migration to prevent errors when rolling back.
    """
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('base', '0002_remove_product_createdtime_and_more'),  # Ensure this points to the correct last migration
    ]

    operations = [
        migrations.RunPython(populate_price_numeric, reverse_code=noop_reverse_code),
    ]
