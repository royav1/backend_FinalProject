# # actions.py

# import os
# import asyncio
# from decimal import Decimal, InvalidOperation
# from rapidfuzz import fuzz
# from asgiref.sync import sync_to_async

# # ✅ Setup Django environment
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproj.settings")
# import django
# django.setup()

# # ✅ Import Django-dependent modules after setup
# from scraper.refinement_scraper import scrape_amazon
# from .email_utils import send_notification_email
# from base.models import Watchlist, PriceHistory


# async def run_scraping():
#     print("Running scraping process...")

#     MIN_SIMILARITY_SCORE = 75  # ✅ Minimum required score for valid product match

#     try:
#         # Step 1: Get all watchlists
#         watchlists = await sync_to_async(lambda: list(Watchlist.objects.prefetch_related("products").all()))()
#         if not watchlists:
#             print("❌ No watchlists found.")
#             return

#         for watchlist in watchlists:
#             print(f"\n📂 Watchlist: '{watchlist.name}'")

#             products = await sync_to_async(lambda: list(watchlist.products.all()))()
#             if not products:
#                 print("ℹ️ This watchlist has no products.")
#                 continue

#             for tracked_product in products:
#                 search_query = tracked_product.title
#                 old_price = tracked_product.price  # Decimal from DB

#                 print(f"\n🔍 Product: {search_query} | Previous Price: ${old_price}")

#                 # Step 2: Scrape Amazon
#                 products_data = await scrape_amazon(search_query=search_query, persist_browser=False)
#                 if not products_data:
#                     print("❌ No products were scraped.")
#                     continue

#                 # Step 3: Find best match
#                 best_match = None
#                 best_score = 0

#                 print("\n📌 Scraped Results:")
#                 for idx, product in enumerate(products_data):
#                     try:
#                         title = product.get("title", "No title")
#                         similarity_score = fuzz.partial_ratio(search_query.lower(), title.lower()) if title else 0

#                         if similarity_score > best_score:
#                             best_score = similarity_score
#                             best_match = {**product, "similarity_score": similarity_score}

#                         print(f"\n🔹 Product {idx + 1}/{len(products_data)}:")
#                         print(f"  Title            : {title}")
#                         print(f"  Price            : {product.get('price', 'N/A')}")
#                         print(f"  Numeric Price    : {product.get('price_numeric', 'N/A')}")
#                         print(f"  Rating           : {product.get('rating', 'N/A')}")
#                         print(f"  Reviews          : {product.get('reviews', 'N/A')}")
#                         print(f"  Availability     : {product.get('availability', 'N/A')}")
#                         print(f"  URL              : {product.get('url', 'No URL')}")
#                         print(f"  Similarity Score : {similarity_score:.2f}%")

#                     except Exception as e:
#                         print(f"⚠️ Error displaying product {idx + 1}: {e}")

#                 # Step 4: Process best match
#                 if best_match and best_match["similarity_score"] >= MIN_SIMILARITY_SCORE:
#                     print("\n🏆 Best Product Match:")
#                     for key, label in {
#                         "title": "Title",
#                         "price": "Price",
#                         "price_numeric": "Price Numeric",
#                         "rating": "Rating",
#                         "reviews": "Reviews",
#                         "availability": "Availability",
#                         "url": "URL",
#                         "similarity_score": "Similarity Score"
#                     }.items():
#                         value = best_match.get(key, "N/A")
#                         print(f"  {label:<17}: {value if key != 'similarity_score' else f'{value:.2f}%'}")

#                     try:
#                         new_price = best_match.get("price_numeric")
#                         new_price_decimal = Decimal(str(new_price)) if new_price is not None else None
#                         availability = best_match.get("availability", "Unknown")
#                         threshold = Decimal("30.0")

#                         # ✅ Save to PriceHistory every time
#                         await sync_to_async(PriceHistory.objects.create)(
#                             product=tracked_product,
#                             price=new_price_decimal,
#                             price_numeric=new_price_decimal,
#                             availability=availability
#                         )
#                         print("🗃️ Price history saved.")

#                         if old_price and new_price_decimal and old_price > new_price_decimal:
#                             drop_percent = ((old_price - new_price_decimal) / old_price) * 100

#                             if drop_percent >= threshold:
#                                 print(f"\n📉 Price dropped by {drop_percent:.2f}% (from ${old_price:.2f} to ${new_price_decimal:.2f})")

#                                 subject = "📉 Price Drop Alert!"
#                                 message = (
#                                     f"{best_match['title']} has dropped in price!\n\n"
#                                     f"Old Price: ${old_price:.2f}\n"
#                                     f"New Price: ${new_price_decimal:.2f}\n"
#                                     f"Drop     : {drop_percent:.2f}%\n\n"
#                                     f"Link: {best_match['url']}"
#                                 )
#                                 send_notification_email(subject, message, ["test@example.com"])
#                             else:
#                                 print(f"\nℹ️ Price dropped by {drop_percent:.2f}%, which is below the {threshold}% threshold.")
#                         else:
#                             print("\nℹ️ No price drop detected or price stayed the same.")

#                     except (InvalidOperation, TypeError) as e:
#                         print(f"❌ Price conversion error: {e}")
#                 else:
#                     print(f"\n❌ No valid match found. Best score: {best_score:.2f}% (Minimum required: {MIN_SIMILARITY_SCORE}%)")

#         print("\n✅ Scraping process completed.")

#     except Exception as e:
#         print(f"❌ Error during scraping process: {e}")


# async def print_price_history():
#     print("\n📊 Fetching price history for all products in each watchlist...\n")

#     try:
#         # Step 1: Fetch all watchlists with their products
#         all_watchlists = await sync_to_async(
#             lambda: list(Watchlist.objects.prefetch_related("products").all())
#         )()

#         if not all_watchlists:
#             print("❌ No watchlists found.")
#             return

#         for watchlist in all_watchlists:
#             watchlist_name = watchlist.name

#             has_products = await sync_to_async(watchlist.products.exists)()
#             if not has_products:
#                 print(f"📁 Watchlist: '{watchlist_name}'\nℹ️ This watchlist has no products.\n")
#                 continue

#             print(f"📁 Watchlist: '{watchlist_name}'")

#             products = await sync_to_async(lambda: list(watchlist.products.all()))()

#             for tracked_product in products:
#                 print(f"🔎 Product: {tracked_product.title if tracked_product else 'No product found'}")

#                 try:
#                     history_entries = await sync_to_async(
#                         lambda: list(tracked_product.price_history.order_by("-date_recorded").all())
#                     )()

#                     if not history_entries:
#                         print("ℹ️ No price history available for this product.\n")
#                         continue

#                     print(f"📜 Price History for '{tracked_product.title}':")
#                     for entry in history_entries:
#                         price = entry.price_numeric if entry.price_numeric is not None else "N/A"
#                         availability = entry.availability if entry.availability else "Unknown"
#                         print(f"• {entry.date_recorded} → ${price} ({availability})")
#                     print("")  # Line break between products

#                 except Exception as e:
#                     print(f"❌ Failed to load price history for '{tracked_product.title}': {e}")

#             # Divider between watchlists
#             print("-" * 60)

#     except Exception as e:
#         print(f"❌ Error fetching price history: {e}")


# if __name__ == "__main__":
#     asyncio.run(run_scraping())
#     asyncio.run(print_price_history())



