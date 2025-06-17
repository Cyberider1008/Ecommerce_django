from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import (
    RegisterView,
    UserDetailView,
    ProductViewSet,
    CartItemView,
    CheckoutView,
    CustomerOrderView,
    VendorOrderView,
    CategoryViewSet,
    ProductSalesSummaryExportView,
    BillingAddressViewSet,
    CountryListAPIView
)

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'billing-addresses', BillingAddressViewSet, basename='billing-address')


urlpatterns = [
    # Auth & User
    path('register/', RegisterView.as_view(), name='register'),
    path('user/', UserDetailView.as_view(), name='user-detail'),

    # JWT Token
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # Category
    
    # Products
    path('', include(router.urls)),

    # Cart
    path('cart/', CartItemView.as_view(), name='cart'),

    # Checkout
    path('checkout/', CheckoutView.as_view(), name='checkout'),

    # Orders
    path('orders/', CustomerOrderView.as_view(), name='customer-orders'),
    path('vendor/orders/', VendorOrderView.as_view(), name='vendor-orders'),
    path('vendor/download-report/', ProductSalesSummaryExportView.as_view(), name='vendor-report'),
    path('countries/', CountryListAPIView.as_view(), name='country-list'),
]
