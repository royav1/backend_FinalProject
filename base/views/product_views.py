# product_views.py

from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from asgiref.sync import async_to_sync
from base.serializers import ProductSerializer
from base.models import Product, TrackedProduct
from scraper.playwright_scraper import scrape_amazon, TEMP_SCRAPE_RESULTS



class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            return Product.objects.filter(user=user)
        return Product.objects.none()
    
@api_view(['GET'])
@permission_classes([IsAuthenticated]) 
def search_product(request):
    query = request.query_params.get('query')
    if not query:
        return Response({"error": "Query parameter is required."}, status=400)

    try:
        depth = int(request.query_params.get('depth', 3))
        if depth < 1 or depth > 10:
            return Response({"error": "Depth must be between 1 and 10."}, status=400)
    except ValueError:
        return Response({"error": "Depth must be an integer."}, status=400)

    user = request.user
    user_id = user.id

    try:
        # ✅ Pass depth to the scraper
        async_to_sync(scrape_amazon)(query, user_id, depth)

        return Response({
            "message": f"Search for '{query}' completed successfully"
        }, status=200)
    except Exception as e:
        print(f"Error during scraping: {e}")
        return Response({"error": f"An error occurred: {str(e)}"}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_tracked_product(request):
    user = request.user
    product_name = request.data.get('product_name')
    target_price_input = request.data.get('target_price')

    if not product_name:
        return Response({"error": "Product name is required."}, status=400)

    try:
        # Convert target_price to Decimal (if provided)
        target_price = None
        if target_price_input:
            try:
                target_price = Decimal(target_price_input)
            except InvalidOperation:
                return Response({"error": "Invalid target_price format. Use a numeric value."}, status=400)

        # Check if the product is already being tracked
        existing_product = TrackedProduct.objects.filter(title=product_name, user=user).first()
        if existing_product:
            return Response({"message": f"Product '{existing_product.title}' is already being tracked."}, status=400)

        # Adjust the current time to GMT+2
        current_time_gmt2 = (timezone.now() + timedelta(hours=2)).replace(microsecond=0)

        # Create the new tracked product
        new_product = TrackedProduct.objects.create(
            user=user,
            title=product_name,
            price=request.data.get('price'),
            target_price=target_price,
            rating=request.data.get('rating'),
            reviews=request.data.get('reviews'),
            availability=request.data.get('availability'),
            date_scraped=current_time_gmt2
        )

        return Response({
            "message": f"Product '{new_product.title}' added to your tracked products.",
            "target_price": float(target_price) if target_price else None
        }, status=201)

    except Exception as e:
        print(f"Error adding tracked product: {e}")
        return Response({"error": f"An issue occurred: {str(e)}"}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_tracked_products(request):
    """
    Fetch the tracked products for the logged-in user.
    """
    user = request.user
    try:
        # Retrieve products tracked by the logged-in user
        tracked_products = TrackedProduct.objects.filter(user=user)

        # Include the product ID and target_price in the serialized data
        data = [
            {
                "id": product.id,
                "user": product.user.username,
                "title": product.title,
                "price": float(product.price) if product.price else None,
                "target_price": float(product.target_price) if product.target_price else None,
                "rating": product.rating,
                "reviews": product.reviews,
                "availability": product.availability,
                "date_scraped": product.date_scraped,
            }
            for product in tracked_products
        ]

        return Response(data, status=200)
    except Exception as e:
        print(f"Error fetching tracked products: {e}")
        return Response({"error": f"An error occurred: {str(e)}"}, status=500)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def set_target_price(request):
    """
    Set or update the target price for a tracked product (specified in the request body).
    """
    user = request.user
    product_id = request.data.get("product_id")
    target_price = request.data.get("target_price")

    if not product_id:
        return Response({"error": "Product ID is required."}, status=400)
    if target_price is None:
        return Response({"error": "Target price is required."}, status=400)

    try:
        product = TrackedProduct.objects.get(id=product_id, user=user)
        product.target_price = Decimal(str(target_price))
        product.save()

        return Response({
            "message": f"Target price set successfully.",
            "product_id": product.id,
            "product_title": product.title,
            "target_price": float(product.target_price)
        }, status=200)

    except TrackedProduct.DoesNotExist:
        return Response({"error": "Product not found or does not belong to the user."}, status=404)
    except InvalidOperation:
        return Response({"error": "Invalid target price format."}, status=400)
    except Exception as e:
        print(f"Error updating target price: {e}")
        return Response({"error": "An unexpected error occurred."}, status=500)
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_scraped_results(request):
    """
    Return temporarily stored scraped products for the logged-in user.
    These are stored in TEMP_SCRAPE_RESULTS during manual scraping.
    """
    user = request.user
    entry = TEMP_SCRAPE_RESULTS.get(user.id)

    if not entry:
        return Response([], status=200)

    # Check expiration (10-minute window)
    created_at = entry.get("timestamp")
    if not created_at or (timezone.now() - created_at > timedelta(minutes=30)):
        TEMP_SCRAPE_RESULTS.pop(user.id, None)
        return Response([], status=200)

    return Response(entry.get("results", []), status=200)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_tracked_product(request, product_id):
    user = request.user

    try:
        product = TrackedProduct.objects.get(id=product_id, user=user)
        product.watchlists.clear()

        for history in product.price_history.all():
            if not history.product_title_snapshot:
                history.product_title_snapshot = product.title
            history.product = None
            history.save()

        product.delete()

        return Response({"message": "Tracked product deleted, price history retained."})

    except TrackedProduct.DoesNotExist:
        return Response({"error": "Product not found or not owned by user."}, status=404)



