# actions.py

import os
import asyncio
from decimal import Decimal, InvalidOperation
from rapidfuzz import fuzz
from asgiref.sync import sync_to_async

# ✅ Django setup only once at the top (safe even if re-imported)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproj.settings")
import django
django.setup()

# ✅ Import Django-dependent modules AFTER setup
from scraper.refinement_scraper import scrape_amazon
from .email_utils import send_notification_email
from base.models import Watchlist, PriceHistory
from scheduled_tasks.sale_events import get_current_sale_event


# This is the main scraping engine, used by:
# 1. The scheduler (for automated runs).
# 2. The manual product refresh (from the frontend).
async def run_scraping(filtered_products=None, event_name=None):
    print("Running scraping process...")

    try:
        # ✅ If called with a specific list of products (e.g., from scheduler)
        if filtered_products is not None:
            products_to_scrape = filtered_products
        else:
            # Default: scrape first product from each watchlist
            watchlists = await sync_to_async(lambda: list(Watchlist.objects.prefetch_related("products").all()))()
            if not watchlists:
                print("❌ No watchlists found.")
                return

            products_to_scrape = []
            for watchlist in watchlists:
                has_products = await sync_to_async(watchlist.products.exists)()
                if has_products:
                    product = await sync_to_async(watchlist.products.first)()
                    if product:
                        products_to_scrape.append(product)

        for tracked_product in products_to_scrape:
            print(f"\n📦 Processing product: {tracked_product.title}")
            search_query = tracked_product.title
            old_price = tracked_product.price
            target_price = tracked_product.target_price

            print(f"\n🔍 Product: {search_query} | Previous Price: ${old_price} | Target Price: ${target_price}")

            # Step 2: Scrape Amazon
            products_data = await scrape_amazon(search_query=search_query, persist_browser=False)
            if not products_data:
                print("❌ No products were scraped.")
                continue

            # Step 3: Find best match
            best_match = None
            best_score = 0

            print("\n📌 Scraped Results:")
            for idx, product in enumerate(products_data):
                try:
                    title = product.get("title", "No title")
                    similarity_score = fuzz.partial_ratio(search_query.lower(), title.lower()) if title else 0

                    if similarity_score > best_score:
                        best_score = similarity_score
                        best_match = {**product, "similarity_score": similarity_score}

                    print(f"\n🔹 Product {idx + 1}/{len(products_data)}:")
                    print(f"  Title            : {title}")
                    print(f"  Price            : {product.get('price', 'N/A')}")
                    print(f"  Numeric Price    : {product.get('price_numeric', 'N/A')}")
                    print(f"  Rating           : {product.get('rating', 'N/A')}")
                    print(f"  Reviews          : {product.get('reviews', 'N/A')}")
                    print(f"  Availability     : {product.get('availability', 'N/A')}")
                    print(f"  URL              : {product.get('url', 'No URL')}")
                    print(f"  Similarity Score : {similarity_score:.2f}%")

                except Exception as e:
                    print(f"⚠️ Error displaying product {idx + 1}: {e}")

            # Step 4: Process best match
            if best_match:
                print("\n🏆 Best Product Match:")
                for key, label in {
                    "title": "Title",
                    "price": "Price",
                    "price_numeric": "Price Numeric",
                    "rating": "Rating",
                    "reviews": "Reviews",
                    "availability": "Availability",
                    "url": "URL",
                    "similarity_score": "Similarity Score"
                }.items():
                    value = best_match.get(key, "N/A")
                    print(f"  {label:<17}: {value if key != 'similarity_score' else f'{value:.2f}%'}")

                try:
                    new_price = best_match.get("price_numeric")
                    new_price_decimal = Decimal(str(new_price)) if new_price is not None else None
                    availability = best_match.get("availability", "Unknown")
                    similarity_threshold = 75.0

                    if best_score < similarity_threshold:
                        print(f"\n🚫 Similarity score {best_score:.2f}% is below the {similarity_threshold}% threshold. Skipping.")
                        continue

                    # ✅ Save to PriceHistory with event_name if available
                    await sync_to_async(PriceHistory.objects.create)(
                        product=tracked_product,
                        product_title_snapshot=tracked_product.title,  # ✅ snapshot
                        price=new_price_decimal,
                        price_numeric=new_price_decimal,
                        availability=availability,
                        event_name=event_name
                    )
                    print(f"🗃️ Price history saved. {'📅 Event: ' + event_name if event_name else ''}")

                    # 🔔 Trigger alert if new price is below target_price
                    if target_price and new_price_decimal and new_price_decimal < target_price:
                        print(f"\n📉 Price dropped below target price (${target_price}): now ${new_price_decimal:.2f}")

                        subject = "📉 Price Alert: Below Target Price!"
                        message = (
                            f"{best_match['title']} has dropped below your target price!\n\n"
                            f"Target Price: ${target_price:.2f}\n"
                            f"Current Price: ${new_price_decimal:.2f}\n\n"
                            f"Link: {best_match['url']}"
                        )

                        # ✅ Get the real user email safely using sync_to_async
                        user_email = await sync_to_async(lambda: tracked_product.user.email)()
                        print(f"📧 Sending alert to: {user_email}")

                        send_notification_email(subject, message, [user_email])
                    else:
                        print("\nℹ️ No alert sent. Price is not below the target.")

                except (InvalidOperation, TypeError) as e:
                    print(f"❌ Price conversion error: {e}")
            else:
                print("\n❌ No best match found.")

        print("\n✅ Scraping process completed.")

    except Exception as e:
        print(f"❌ Error during scraping process: {e}")


async def print_price_history():
    print("\n📊 Fetching price history for the first product in each watchlist...\n")

    try:
        all_watchlists = await sync_to_async(
            lambda: list(Watchlist.objects.prefetch_related("products").all())
        )()

        if not all_watchlists:
            print("❌ No watchlists found.")
            return

        for watchlist in all_watchlists:
            watchlist_name = watchlist.name

            has_products = await sync_to_async(watchlist.products.exists)()
            if not has_products:
                print(f"📁 Watchlist: '{watchlist_name}'\nℹ️ This watchlist has no products.\n")
                continue

            print(f"📁 Watchlist: '{watchlist_name}'")

            tracked_product = await sync_to_async(watchlist.products.first)()
            print(f"🔎 Product: {tracked_product.title if tracked_product else 'No product found'}")

            try:
                history_entries = await sync_to_async(
                    lambda: list(tracked_product.price_history.order_by("-date_recorded").all())
                )()

                if not history_entries:
                    print("ℹ️ No price history available for this product.\n")
                    continue

                print(f"📜 Price History for '{tracked_product.title}':")
                for entry in history_entries:
                    price = entry.price_numeric if entry.price_numeric is not None else "N/A"
                    availability = entry.availability if entry.availability else "Unknown"
                    print(f"• {entry.date_recorded} → ${price} ({availability})")
                print("")  # Line break between products

            except Exception as e:
                print(f"❌ Failed to load price history for '{tracked_product.title}': {e}")

            print("-" * 60)

    except Exception as e:
        print(f"❌ Error fetching price history: {e}")


# ✅ Safe CLI entry point — only runs on `python -m scheduled_tasks.actions`
if __name__ == "__main__" and __package__ == "scheduled_tasks":
    current_event = get_current_sale_event()
    asyncio.run(run_scraping(event_name=current_event))  # ✅ inject event
    asyncio.run(print_price_history())
