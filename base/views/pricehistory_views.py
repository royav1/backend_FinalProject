from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from base.models import PriceHistory  
from datetime import timedelta
from django.utils.timezone import now
from django.db import models
from django.db.models import Func, F

# SQL-level TRIM for reliable comparison. 
# Trim removes any spaces at the beginning and the end of the event's name
class Trim(Func):
    function = 'TRIM'
    arity = 1

# This function returns the price history for a specific tracked product or a deleted product (via snapshot title), 
# so I can delete a product from the tracked products list but maintain it's price history with "product_title_snapshot"
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_price_history(request, product_id=None, title=None):
    """
    Retrieve price history for a given tracked product (by ID) or deleted product title (snapshot),
    filtered by date (?days=...) and optionally by sale event (?event=...).
    """
    user = request.user

    try:
        days = int(request.GET.get('days', 30))
        days = max(1, min(days, 365))
        since_date = now() - timedelta(days=days)
        event_filter = request.GET.get('event', '').strip()

        history_qs = PriceHistory.objects.none()

        if title:
            # Snapshot mode
            snapshot_title = title.strip()
            history_qs = PriceHistory.objects.filter(
                product__isnull=True,
                product_title_snapshot=snapshot_title,
                date_recorded__gte=since_date
            )
        else:
            # Regular product mode
            history_qs = PriceHistory.objects.filter(
                product__id=product_id,
                product__user=user,
                date_recorded__gte=since_date
            )

        if event_filter:
            history_qs = history_qs.annotate(
                clean_event=Trim(F('event_name'))
            ).filter(clean_event__iexact=event_filter)

        history_entries = history_qs.order_by("-date_recorded")

        if not history_entries.exists():
            return Response({"message": "No price history found for this product."}, status=404)

        first_entry = history_entries.first()
        product_title = (
            first_entry.product.title
            if first_entry.product else first_entry.product_title_snapshot
        )
        target_price = (
            float(first_entry.product.target_price)
            if first_entry.product and first_entry.product.target_price is not None
            else None
        )

        serialized_history = [
            {
                "date_recorded": entry.date_recorded,
                "price_numeric": float(entry.price_numeric) if entry.price_numeric is not None else None,
                "availability": entry.availability,
                "event_name": entry.event_name,
                "product_title": entry.product.title if entry.product else entry.product_title_snapshot
            }
            for entry in history_entries
        ]

        return Response({
            "product_title": product_title,
            "target_price": target_price,
            "price_history": serialized_history
        }, status=200)

    except Exception as e:
        return Response({"error": "An unexpected error occurred."}, status=500)

# Returns all unique product titles (tracked and deleted) for which the user has at least one price history entry
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_products_with_price_history(request):
    user = request.user

    # Get all price history entries for this user’s products (even deleted ones)
    history_entries = (
        PriceHistory.objects
        .filter(models.Q(product__user=user) | models.Q(product__isnull=True))
        .exclude(product_title_snapshot__isnull=True)
        .order_by('-date_recorded')
    )

    seen_titles = set()
    unique_titles = []

    for entry in history_entries:
        title = entry.product.title if entry.product else entry.product_title_snapshot
        if title not in seen_titles:
            seen_titles.add(title)
            unique_titles.append({
                "id": entry.product.id if entry.product else f"snapshot:{title}",
                "title": title
            })

    return Response(unique_titles)
