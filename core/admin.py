from django.contrib import admin
from .models import User, Category, Product, CartItem, Order, OrderItem, BillingAddress

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'is_active')

# class ProductAdmin(admin.ModelAdmin):
#     list_display = ('id', 'name', 'is_active')

class BillingAddressAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'country', 'city')
    
class ProductInline(admin.TabularInline):
    model = Product
    extra = 0

class VendorAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'role']
    inlines = [ProductInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(role='vendor')





# Register your models here.
# admin.site.register(User)
admin.site.register(Category, CategoryAdmin)
# admin.site.register(Product, ProductAdmin)
admin.site.register(CartItem)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(BillingAddress, BillingAddressAdmin)
admin.site.register(User, VendorAdmin)
admin.site.register(Product)
