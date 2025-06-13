from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Product, CartItem, Order, OrderItem, Category

User = get_user_model()

# User Serializer (for registration & profile)
class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'role']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email'),
            password=validated_data['password'],
            role=validated_data['role']
        )
        return user



# category Serializers
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

# Product Serializer
class ProductSerializer(serializers.ModelSerializer):
    vendor = serializers.ReadOnlyField(source='vendor.username')

    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'price', 'image', 'vendor','stock', "category", 'is_active', 'created_at']


# Cart Item Serializer
class CartItemSerializer(serializers.ModelSerializer):
    product_detail = ProductSerializer(source='product', read_only=True)
    product = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'quantity', 'product_detail']


# Order Item Serializer (nested inside Order)
class OrderItemSerializer(serializers.ModelSerializer):
    product_detail = ProductSerializer(source='product', read_only=True)
    subtotal = serializers.SerializerMethodField()
    product = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'quantity', 'product_detail','subtotal']

    def get_subtotal(self, obj):
        return float(obj.product.price) * obj.quantity


# Order Serializer
class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    total_amount = serializers.SerializerMethodField()
    customer = serializers.StringRelatedField(source='customer.username', read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'customer', 'ordered_at', 'is_paid', 'items','total_amount']
        
    def get_total_amount(self, obj):
        return sum([
            item.product.price * item.quantity for item in obj.items.all()
        ])