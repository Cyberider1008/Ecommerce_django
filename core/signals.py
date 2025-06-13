from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import OrderItem, Category, Product

@receiver(post_save, sender=OrderItem)
def update_stock_on_order(sender, instance, created, **kwargs):
    if created:
        product = instance.product
        if product.stock >= instance.quantity:
            product.stock -= instance.quantity
            product.save()
        else:
            raise ValueError(f"Not enough stock for {product.name}")
@receiver(post_save, sender=Category)
def update_products_active_status(sender, instance, **kwargs):
    # Sync product is_active with category is_active
    print(instance.is_active)
    Product.objects.filter(category=instance).update(is_active=instance.is_active)