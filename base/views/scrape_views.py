from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from base.models import TrackedProduct, PriceHistory
from scheduled_tasks.actions import run_scraping
from asgiref.sync import async_to_sync
from django.conf import settings  # ✅ Import settings for DEFAULT_FROM_EMAIL


# allows a logged-in user to manually trigger price scraping for a specific product they are tracking
# before_count- Stores the number of history entries before scraping, used to detect if a new entry was added after scraping
# after_history- Checks if a new history entry was added after scraping, If so, grabs the latest entry,
# finely sends an alert if The new scraped price is lower than the target price.
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def scrape_single_product(request, product_id):
    try:
        product = TrackedProduct.objects.get(id=product_id, user=request.user)
        print(f"🔁 Manually triggering scrape for: {product.title}")

        # Get previous price history count to detect new entry later
        before_count = PriceHistory.objects.filter(product=product).count()

        # Run scraping for this single product
        async_to_sync(run_scraping)(filtered_products=[product])

        # Get new price history count and latest entry
        after_history = PriceHistory.objects.filter(product=product).order_by('-date_recorded')
        after_count = after_history.count()
        alert_sent = False

        if after_count > before_count:
            latest = after_history.first()
            alert_sent = (
                product.target_price is not None and
                latest.price_numeric is not None and
                latest.price_numeric < product.target_price
            )

        return Response({
            "results": [{
                "product_id": product.id,
                "title": product.title,
                "alert_sent": alert_sent,
                "from_email": settings.DEFAULT_FROM_EMAIL,
                "to_email": request.user.email
            }]
        })

    except TrackedProduct.DoesNotExist:
        return Response({"error": "Product not found or unauthorized."}, status=404)
    except Exception as e:
        return Response({"error": str(e)}, status=500)
