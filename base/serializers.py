from rest_framework import serializers
from .models import Product, SearchResult, Watchlist, TrackedProduct, PriceHistory


class SearchResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchResult
        fields = ['product_name', 'product_url', 'price', 'query', 'created_at']


class ProductSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    search_result = SearchResultSerializer()

    class Meta:
        model = Product
        fields = ['id', 'user', 'created_at', 'price', 'search_result']


class TrackedProductSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()

    class Meta:
        model = TrackedProduct
        fields = ['id', 'user', 'title', 'price', 'target_price', 'rating', 'reviews',
            'availability', 'date_scraped'
        ]
        extra_kwargs = {
            'price': {'max_digits': 10, 'decimal_places': 2},
            'target_price': {'max_digits': 10, 'decimal_places': 2},
            'rating': {'max_digits': 3, 'decimal_places': 1},
        }


class SimpleTrackedProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrackedProduct
        fields = [
            'id', 'title', 'price', 'target_price', 'rating', 'reviews',
            'availability', 'date_scraped'
        ]


class PriceHistorySerializer(serializers.ModelSerializer):
    product = TrackedProductSerializer()
    product_title_snapshot = serializers.CharField(read_only=True)

    class Meta:
        model = PriceHistory
        fields = [
            'product', 'product_title_snapshot', 'price', 'price_numeric', 'availability',
            'date_recorded', 'event_name'
        ]
        extra_kwargs = {
            'price': {'max_digits': 10, 'decimal_places': 2},
            'price_numeric': {'max_digits': 10, 'decimal_places': 2},
        }


class SimplePriceHistorySerializer(serializers.ModelSerializer):
    product_title_snapshot = serializers.CharField(read_only=True)

    class Meta:
        model = PriceHistory
        fields = [
            'price_numeric', 'availability', 'date_recorded', 'event_name','product_title_snapshot'
        ]


class WatchlistSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    products = TrackedProductSerializer(many=True, read_only=True)

    class Meta:
        model = Watchlist
        fields = [
            'id', 'user', 'name', 'products', 'created_at', 'updated_at',
            'scheduled_scraping_enabled', 'scraping_time'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at']
