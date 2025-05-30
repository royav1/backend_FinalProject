# watchlist_views.py

from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from base.serializers import WatchlistSerializer
from base.models import Watchlist, TrackedProduct


class WatchlistViewSet(viewsets.ModelViewSet):
    serializer_class = WatchlistSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Watchlist.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_watchlist(request):
    name = request.data.get('name')
    if not name:
        return Response({"error": "Watchlist name is required."}, status=400)

    watchlist = Watchlist.objects.create(user=request.user, name=name)
    return Response({"message": f"Watchlist '{watchlist.name}' created successfully."}, status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_watchlists(request):
    user = request.user
    watchlists = Watchlist.objects.filter(user=user)
    serializer = WatchlistSerializer(watchlists, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_products_to_watchlist(request):
    watchlist_id = request.data.get('watchlist_id')
    product_ids = request.data.get('product_ids')

    if not watchlist_id or not product_ids:
        return Response({"error": "watchlist_id and product_ids are required."}, status=400)

    watchlist = get_object_or_404(Watchlist, id=watchlist_id, user=request.user)

    for product_id in product_ids:
        try:
            product = TrackedProduct.objects.get(id=product_id, user=request.user)
            watchlist.products.add(product)
        except TrackedProduct.DoesNotExist:
            return Response({"error": f"Product with ID {product_id} not found or does not belong to user."}, status=404)

    watchlist.save()
    return Response({"message": "Products added to watchlist successfully."})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_watchlist(request, watchlist_id):
    try:
        watchlist = Watchlist.objects.get(id=watchlist_id, user=request.user)
        watchlist.delete()
        return Response({"message": "Watchlist deleted successfully."})
    except Watchlist.DoesNotExist:
        return Response({"error": "Watchlist not found or does not belong to the user."}, status=404)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def change_watchlist_name(request, watchlist_id):
    new_name = request.data.get('name')
    if not new_name:
        return Response({"error": "New watchlist name is required."}, status=400)

    try:
        watchlist = Watchlist.objects.get(id=watchlist_id, user=request.user)
        watchlist.name = new_name
        watchlist.save()
        return Response({"message": "Watchlist name updated successfully."})
    except Watchlist.DoesNotExist:
        return Response({"error": "Watchlist not found or does not belong to the user."}, status=404)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_product_from_watchlist(request, watchlist_id, product_id):
    try:
        watchlist = Watchlist.objects.get(id=watchlist_id, user=request.user)
        product = TrackedProduct.objects.get(id=product_id, user=request.user)
        watchlist.products.remove(product)
        return Response({"message": "Product removed from watchlist successfully."})
    except (Watchlist.DoesNotExist, TrackedProduct.DoesNotExist):
        return Response({"error": "Watchlist or product not found or not owned by user."}, status=404)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_watchlist_products(request, watchlist_id):
    try:
        watchlist = Watchlist.objects.get(id=watchlist_id, user=request.user)
        products = watchlist.products.all()
        data = [{
            "id": product.id,
            "title": product.title,
            "price": float(product.price) if product.price else None,
            "availability": product.availability,
            "target_price": float(product.target_price) if product.target_price else None,
            "rating": product.rating,
            "reviews": product.reviews,
            "date_scraped": product.date_scraped
        } for product in products]
        return Response(data, status=200)
    except Watchlist.DoesNotExist:
        return Response({"error": "Watchlist not found or does not belong to the user."}, status=404)

# 🚫 Not currently used in frontend.
# This endpoint allows enabling/disabling scheduled scraping per watchlist.
# Currently, only global scraping control is exposed to users via the UI.
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def toggle_watchlist_scraping(request, watchlist_id):
    """
    Enable or disable scheduled scraping for a specific watchlist.
    """
    user = request.user
    enabled = request.data.get("enabled")

    if enabled is None:
        return Response({"error": "Missing 'enabled' parameter."}, status=400)

    try:
        watchlist = Watchlist.objects.get(id=watchlist_id, user=user)
        watchlist.scheduled_scraping_enabled = bool(enabled)
        watchlist.save()
        return Response({
            "message": f"Scheduled scraping {'enabled' if enabled else 'disabled'} for '{watchlist.name}'.",
            "watchlist_id": watchlist.id,
            "enabled": watchlist.scheduled_scraping_enabled
        }, status=200)
    except Watchlist.DoesNotExist:
        return Response({"error": "Watchlist not found or unauthorized."}, status=404)
