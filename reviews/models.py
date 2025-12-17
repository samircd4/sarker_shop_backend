from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Avg

from products.models import Product
from accounts.models import Customer


class Review(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='reviews')
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name='product_reviews')

    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'customer')

    def __str__(self):
        return f"{self.rating}★ - {self.customer.name}"


@receiver([post_save, post_delete], sender=Review)
def update_product_rating(sender, instance, **kwargs):
    product = instance.product
    aggregate_data = Review.objects.filter(product=product).aggregate(
        avg_rating=Avg('rating'),
        count=models.Count('id')
    )
    product.rating = aggregate_data['avg_rating'] or 0.0
    product.reviews_count = aggregate_data['count'] or 0
    product.save()
