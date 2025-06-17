from django.contrib import admin
from .models import User, Category, Product, CartItem, Order, OrderItem, BillingAddress

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'is_active')

class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'is_active')

class BillingAddressAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'country', 'city')
    


# Register your models here.
admin.site.register(User)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(CartItem)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(BillingAddress, BillingAddressAdmin)