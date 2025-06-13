from django.contrib import admin
from .models import User, Category, Product, CartItem, Order, OrderItem

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')

class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    


# Register your models here.
admin.site.register(User)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(CartItem)
admin.site.register(Order)
admin.site.register(OrderItem)