from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Product,
    CartItem,
    Order, 
    OrderItem,
    Category,
    BillingAddress,
)

from .models import Product, CartItem, Order, OrderItem, Category, BillingAddress
from decimal import Decimal

User = get_user_model()
# User Serializer (for registration & profile)
class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'role']

    # def get_is_admin(self, obj):
    #     return obj.is_superuser

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.is_superuser:
            data['role'] = 'admin'
        return data    

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
        fields = ['id', 'name', 'is_active']

# Product Serializer
class ProductSerializer(serializers.ModelSerializer):
    vendor = serializers.ReadOnlyField(source='vendor.username')
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    category_name = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
    'id',
    'name',
    'description',
    'price',
    'image',
    'vendor',
    'category_name',
    'stock',
    'category',
    'is_active',
    'created_at',
]
    def get_category_name(self, obj):
        return obj.category.name if obj.category else None
    
    def validate_category(self, value):
        if not value.is_active:
            raise serializers.ValidationError("Selected category is not active.")
        return value


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
# class OrderSerializer(serializers.ModelSerializer):
#     items = OrderItemSerializer(many=True, read_only=True)
#     total_amount = serializers.SerializerMethodField()
#     customer = serializers.StringRelatedField(source='customer.username', read_only=True)

#     class Meta:
#         model = Order
#         fields = ['id', 'customer', 'ordered_at', 'is_paid', 'items','total_amount']
        
#     def get_total_amount(self, obj):
#         return sum([
#             item.product.price * item.quantity for item in obj.items.all()
#         ])

# aniket here
class OrderSerializer(serializers.ModelSerializer):
    subtotal_amount = serializers.SerializerMethodField()
    total_tax = serializers.SerializerMethodField()
    final_total = serializers.SerializerMethodField()
    products = serializers.SerializerMethodField()
    customer = serializers.StringRelatedField(source='customer.username', read_only=True)
 
    class Meta:
        model = Order
        fields = [
            'id', 'customer', 'ordered_at', 'is_paid',
            'products',
            'subtotal_amount', 'total_tax', 'final_total'
        ]
 
    def get_products(self, obj):
        return [
            {
                "product_name": item.product.name,
                "image": item.product.image.url if item.product.image else None,
                "quantity": item.quantity,
                "price": float(item.product.price)  
            }
            for item in obj.items.all()
        ]
 
    def get_subtotal_amount(self, obj):
        return sum(item.product.price * item.quantity for item in obj.items.all())
 
    def get_total_tax(self, obj):
        subtotal = self.get_subtotal_amount(obj)
        return float(round(Decimal(subtotal) * Decimal('0.10'), 2))
 
    def get_final_total(self, obj):
        subtotal = Decimal(self.get_subtotal_amount(obj))
        tax = Decimal(self.get_total_tax(obj))
        return float(round(subtotal + tax, 2))
    
    
class BillingAddressSerializer(serializers.ModelSerializer):
    country_display = serializers.CharField(source='get_country_display', read_only=True)

    class Meta:
        model = BillingAddress
        fields = '__all__'
        read_only_fields = ['user', 'created_at']