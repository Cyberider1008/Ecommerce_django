from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import OrderItem

@receiver(post_save, sender=OrderItem)
def update_stock_on_order(sender, instance, created, **kwargs):
    if created:
        product = instance.product
        if product.stock >= instance.quantity:
            product.stock -= instance.quantity
            product.save()
        else:
            raise ValueError(f"Not enough stock for {product.name}")
