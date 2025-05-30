# urls.py

from django.urls import include, path
from rest_framework.routers import DefaultRouter

# Import views split by functionality
from base.views.auth_views import (
    register, custom_login, user_logout, get_user_info, get_scraping_setting, backfill_userprofiles, toggle_scraping_setting
)
from base.views.product_views import (
    search_product, add_tracked_product, get_tracked_products, set_target_price, ProductViewSet, get_scraped_results, delete_tracked_product
)
from base.views.watchlist_views import (
    create_watchlist, get_user_watchlists, add_products_to_watchlist,
    delete_watchlist, change_watchlist_name,
    remove_product_from_watchlist, get_watchlist_products, toggle_watchlist_scraping, WatchlistViewSet
)
from base.views.pricehistory_views import get_price_history, get_products_with_price_history
from base.views.searchresult_views import SearchResultViewSet
from base.views.misc_views import index
from base.views.scrape_views import scrape_single_product
from base.views.sale_views import get_sale_events

# Set up router
router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='products')
router.register(r'search-results', SearchResultViewSet, basename='search-results')
router.register(r'watchlists', WatchlistViewSet, basename='watchlists')

urlpatterns = [
    path('', index, name='index'),  # Root endpoint
    path('register/', register, name='register'),  # User registration
    path('login/', custom_login, name='login'),  # JWT login
    path('logout/', user_logout, name='logout'),  # User logout
    path('user-info/', get_user_info, name='get-user-info'),  # User info endpoint
    path('check-scraping-setting/', get_scraping_setting, name='check-scraping-setting'),
    path('backfill-userprofiles/', backfill_userprofiles, name='backfill-userprofiles'),

    path('search/', search_product, name='search'),
    path('add-tracked-product/', add_tracked_product, name='add-tracked-product'),
    path('get-tracked-products/', get_tracked_products, name='get-tracked-products'),
    path('set-target-price/', set_target_price, name='set-target-price'),
    path('get-scraped-results/', get_scraped_results, name='get-scraped-results'),
    path('tracked-product/<int:product_id>/', delete_tracked_product, name='delete-tracked-product'),

    path('create-watchlist/', create_watchlist, name='create-watchlist'),
    path('get-user-watchlists/', get_user_watchlists, name='get-user-watchlists'),
    path('add-products-to-watchlist/', add_products_to_watchlist, name='add-products-to-watchlist'),
    path('delete-watchlist/<int:watchlist_id>/', delete_watchlist, name='delete-watchlist'),
    path('change-watchlist-name/<int:watchlist_id>/', change_watchlist_name, name='change-watchlist-name'),
    path('remove-product-from-watchlist/<int:watchlist_id>/<int:product_id>/', remove_product_from_watchlist, name='remove-product-from-watchlist'),
    path('watchlist-products/<int:watchlist_id>/', get_watchlist_products, name='get-watchlist-products'),
    path('toggle-watchlist-scraping/<int:watchlist_id>/', toggle_watchlist_scraping, name='toggle-watchlist-scraping'),
    path('toggle-scraping-setting/', toggle_scraping_setting, name='toggle-scraping-setting'),

    # 🆕 Correct: snapshot title route with slash
    path('price-history/snapshot/<path:title>/', get_price_history, name='get-price-history-snapshot'),
    path('price-history/<int:product_id>/', get_price_history, name='get-price-history'),

    path('products-with-history/', get_products_with_price_history, name='products-with-history'),

    path('scrape/<int:product_id>/', scrape_single_product),
    path('sale-events/', get_sale_events),

    path('', include(router.urls)),  # Include router-generated URLs for viewsets
]
