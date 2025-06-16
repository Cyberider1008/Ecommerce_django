import os
from io import BytesIO
import pandas as pd

from rest_framework import generics, permissions, status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated,SAFE_METHODS, BasePermission

from django.contrib.auth import get_user_model
from django.conf import settings


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


class IsAdminOrVendor(BasePermission):
    """
    Allow only Admin and Vendor to add or modify products.
    Everyone (authenticated or not) can read (GET, HEAD, OPTIONS).
    """

    def has_permission(self, request, view):
        # Allow all safe methods (e.g. GET, HEAD, OPTIONS)
        if request.method in SAFE_METHODS:
            return True

        # Allow only if user is authenticated and is admin or vendor
        return (
            request.user.is_authenticated and
            (request.user.is_superuser or request.user.role == 'vendor')
        )


class IsCustomer(BasePermission):
    """
    Read for all authenticated users. Write only for customers.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user.is_authenticated  # any authenticated user can read
        return request.user.is_authenticated and request.user.role == 'customer'


# Register API
class RegisterView(APIView):
    
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
    permission_classes = [IsAdminOrVendor]

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
    permission_classes = [IsCustomer]

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
    permission_classes = [IsCustomer]

    def post(self, request):
        cart_items = CartItem.objects.filter(customer=request.user)
        if not cart_items.exists():
            return Response({"error": "Cart is empty."}, status=400)
        
         # Validate stock for all items before proceeding
        for item in cart_items:
            product = item.product
            if item.quantity > product.stock:
                return Response({
                    "error": f"Not enough stock for '{product.name}'. Available: {product.stock}, In Cart: {item.quantity}"
                }, status=400)

        order = Order.objects.create(customer=request.user)
        for item in cart_items:
            product = item.product

            # Deduct stock
            product.stock -= item.quantity
            product.save()

            # Create order item
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item.quantity
            )
            
        cart_items.delete()
        return Response({"success": f"Order #{order.id} placed!"})


# Orders
class CustomerOrderView(APIView):
    permission_classes = [IsAuthenticated, IsCustomer]

    def get(self, request):
        orders = Order.objects.filter(customer=request.user)
        if not orders.exists():
            return Response({"detail": "No orders found."}, status=status.HTTP_204_NO_CONTENT)

        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class VendorOrderView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrVendor]

    def get(self, request):
        vendor = request.user
        order_ids = OrderItem.objects.filter(product__vendor=vendor).values_list('order_id', flat=True)
        orders = Order.objects.filter(id__in=order_ids).prefetch_related('items', 'items__product')
        
        if not orders.exists():
            return Response({"detail": "No orders found."}, status=status.HTTP_204_NO_CONTENT)

        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)  

class ProductSalesSummaryExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # Get all OrderItems where product vendor is request.user
            order_items = OrderItem.objects.filter(product__vendor=request.user)

            sales_summary = {}

            for item in order_items:
                product = item.product
                product_id = product.id

                if product_id not in sales_summary:
                    sales_summary[product_id] = {
                        'Product Name': product.name,
                        'Category': product.category.name if product.category else 'N/A',
                        'Unit Price': float(product.price),
                        'Total Quantity Sold': 0,
                        'Total Revenue': 0,
                    }

                sales_summary[product_id]['Total Quantity Sold'] += item.quantity
                sales_summary[product_id]['Total Revenue'] += float(product.price) * item.quantity

            # Convert to DataFrame
            df = pd.DataFrame(sales_summary.values())
            df = df.sort_values(by='Product Name')

            # Create Excel file in memory
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Sales Summary', index=False, startrow=1, header=False)

                workbook = writer.book
                worksheet = writer.sheets['Sales Summary']
                header_format = workbook.add_format({'bold': True})

                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)

            output.seek(0)

            # Save to media directory
            file_path = os.path.join(settings.MEDIA_ROOT, 'product_sales_summary.xlsx')
            os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
            with open(file_path, 'wb') as f:
                f.write(output.getvalue())

            # Return download link
            file_url = request.build_absolute_uri(os.path.join(settings.MEDIA_URL, 'product_sales_summary.xlsx'))
            return Response({'download_link': file_url}, status=200)

        except Exception as e:
            return Response(f"Error generating report: {str(e)}", status=500)