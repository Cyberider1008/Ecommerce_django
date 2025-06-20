import os
import random
from io import BytesIO
import pandas as pd
from threading import Thread

from django.core.mail import EmailMultiAlternatives
from django.contrib.auth import get_user_model
from django.conf import settings
from django.template.loader import render_to_string
from django_countries import countries

from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import permissions, status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response

from rest_framework.permissions import (
    IsAuthenticated,
    SAFE_METHODS,
    BasePermission,
    IsAuthenticatedOrReadOnly,
    AllowAny,
)


from .models import (
    Product,
    CartItem,
    Order,
    OrderItem,
    Category,
    BillingAddress,
    EmailOTP,
)

from .serializers import (
    UserSerializer,
    ProductSerializer,
    CartItemSerializer,
    OrderSerializer,
    CategorySerializer,
    BillingAddressSerializer,
)

User = get_user_model()

class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:  # GET, HEAD, OPTIONS
            return True
        return request.user.is_staff

class IsAdminOrVendor(BasePermission):
   
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        # Allow only if user is authenticated and is admin or vendor
        return (
            request.user.is_authenticated and
            (request.user.is_superuser or request.user.role == 'vendor')
        )

class IsCustomer(BasePermission):
    
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
            # Send welcome email
            subject = "Registration Successful"
            username = user.username
            email = user.email

            from_email = "noreply.it@gmail.com"
            to_email = [email]

            context = {"username": username, "role": user.role}
            html_content = render_to_string("core/emails/registration.html", context)
            text_content = "registration here!"

            def send_otp_email():
                try:
                    email_message = EmailMultiAlternatives(
                        subject, text_content, from_email, to_email
                    )
                    email_message.attach_alternative(html_content, "text/html")
                    email_message.send(fail_silently = False)
                except Exception as e:
                    print("Error sending email:", e)

            Thread(target = send_otp_email).start()

            return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SendOTPAPIView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        
        email = request.data.get('email')
        
        user = User.objects.filter(email=email).first()
       
        if not user:
            print("hello")
            return Response({"error": "User not 1found"}, status=404)

        otp = random.randint(10000, 99999)
        username = user.username
        request.session['username'] = username

        EmailOTP.objects.create(username=username, otp=otp)

        subject = "Send OTP Successful"
        from_email = "noreply.it@gmail.com"
        to_email = [user.email]
        context = {"username": username, "otp": otp}
        html_content = render_to_string("core/emails/otp.html", context)

        def send_otp_email():
            try:
                email_message = EmailMultiAlternatives(subject, "OTP here!", from_email, to_email)
                email_message.attach_alternative(html_content, "text/html")
                email_message.send(fail_silently=False)
            except Exception as e:
                print("Error sending email:", e)

        Thread(target=send_otp_email).start()

        return Response({"message": "OTP sent successfully"})

class VerifyOTP(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        otp = request.data.get('otp')
        username = request.session.get('username')

        if not username or not otp:
            return Response({"error": "OTP and session required"}, status=400)

        try:
            
            otp_obj = EmailOTP.objects.filter(username=username, otp=otp).latest('created_at')

            if otp_obj.is_expired():
                return Response({"error": "OTP expired"}, status=400)

            request.session['otp_verified'] = True
            return Response({"message": "OTP verified successfully"})

        except (User.DoesNotExist, EmailOTP.DoesNotExist):
            return Response({"error": "Invalid OTP or session"}, status=400)
        

class ResetPasswordAPIView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        username = request.session.get('username')
        otp_verified = request.session.get('otp_verified', False)
        new_password = request.data.get('new_password')

        if not username or not otp_verified:
            return Response({'error': 'OTP verification required'}, status=400)

        try:
            user = User.objects.get(username=username)
            user.set_password(new_password)
            user.save()

            # Clean session & delete OTPs
            EmailOTP.objects.filter(username=username).delete()
            request.session.flush()  # clear session securely

            return Response({'message': 'Password reset successfully'}, status=200)

        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=400)
        


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
    
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticatedOrReadOnly] 
    parser_classes = [MultiPartParser, FormParser]
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminOrVendor()]  # Only vendor or admin can modify
        return super().get_permissions()  # Anyone can viewx    

    def perform_create(self, serializer):
        if not self.request.user.is_vendor():
            return Response({"error": "Only vendors can add products."}, status=403)
        serializer.save(vendor=self.request.user)

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            if user.is_vendor():
                return Product.objects.filter(vendor=user)
            elif user.is_staff:
                return Product.objects.all()
        return Product.objects.filter(is_active=True)

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
            if quantity is None or int(quantity) >= product.stock:
                return Response({'error': f"Not enough stock for '{product.name}'. Available: {product.stock}, In Cart: {quantity}"}, status=400) 
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
    
    def put(self, request):
        """Update quantity of an item"""
        product_id = request.data.get('product')
        quantity = int(request.data.get('quantity', 1))

        try:
            item = CartItem.objects.get(customer=request.user, product_id=product_id)
        except CartItem.DoesNotExist:
            return Response({'error': 'Cart item not found.'}, status=404)

        if quantity < 1 or quantity > item.product.stock:
            return Response({'error': f"Invalid quantity. Max available: {item.product.stock}"}, status=400)

        item.quantity = quantity
        item.save()
        return Response(CartItemSerializer(item).data)

    def delete(self, request):
        product_id = request.data.get('product')

        try:
            item = CartItem.objects.get(customer=request.user, product_id=product_id)
            item.delete()
            return Response({'message': 'Item removed from cart.'}, status=204)
        except CartItem.DoesNotExist:
            return Response({'error': 'Cart item not found.'}, status=404)

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


class OrderSummaryView(APIView):
    permission_classes = [IsAuthenticated]
 
    def get(self, request):
        try:
            # Get latest unpaid order for current customer
            order = Order.objects.filter(customer=request.user).order_by('-ordered_at').first()
 
            if not order:
                return Response({"detail": "No recent orders found."}, status=204)
 
            serializer = OrderSerializer(order)
            return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=500)
 

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

# Billing Address
class BillingAddressViewSet(viewsets.ModelViewSet):
    serializer_class = BillingAddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BillingAddress.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class CountryListAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        country_data =[]
        # Get all countries from django_countries
        for code, name in list(countries):      
            # Filter out countries with empty names
            if name:
                country_data.append({"code": code, "name": name})
        # country_data = [{"code": code, "name": name} for code, name in list(countries)]
        return Response(country_data)
    
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
  