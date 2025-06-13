from rest_framework import generics, permissions, status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated,SAFE_METHODS, BasePermission
from django.contrib.auth import get_user_model

from .models import Product, CartItem, Order, OrderItem, Category
from .serializers import (
    UserSerializer,
    ProductSerializer,
    CartItemSerializer,
    OrderSerializer,
    CategorySerializer,
)

User = get_user_model()

class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:  # GET, HEAD, OPTIONS
            return True
        return request.user.is_staff


# Register API
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer


# Authenticated User Info
class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)




class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]

# Product ViewSet (for vendors)
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        if not self.request.user.is_vendor():
            return Response({"error": "Only vendors can add products."}, status=403)
        serializer.save(vendor=self.request.user)

    def get_queryset(self):
        if self.request.user.is_vendor():
            return Product.objects.filter(vendor=self.request.user)
        return Product.objects.all()


# Cart Views
class CartItemView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = CartItem.objects.filter(customer=request.user)
        serializer = CartItemSerializer(items, many=True)
        return Response(serializer.data)

    def post(self, request):
        product_id = request.data.get('product')
        quantity = request.data.get('quantity', 1)
        try:
            product = Product.objects.get(id=product_id)
            item, created = CartItem.objects.get_or_create(
                customer=request.user,
                product=product,
                defaults={'quantity': quantity}
            )
            if not created:
                item.quantity += int(quantity)
                item.save()
            return Response(CartItemSerializer(item).data)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found.'}, status=404)


# Checkout API
class CheckoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cart_items = CartItem.objects.filter(customer=request.user)
        if not cart_items.exists():
            return Response({"error": "Cart is empty."}, status=400)

        order = Order.objects.create(customer=request.user)
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity
            )
        cart_items.delete()
        return Response({"success": f"Order #{order.id} placed!"})


# Orders
class CustomerOrderView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(customer=self.request.user)

class VendorOrderView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        vendor = self.request.user
        order_ids = OrderItem.objects.filter(product__vendor=vendor).values_list('order_id', flat=True)
        return Order.objects.filter(id__in=order_ids).prefetch_related('items', 'items__product')