from django_filters import FilterSet, CharFilter
from .models import Product, Category
class ProductFilter(FilterSet):
    name = CharFilter(lookup_expr='icontains')
    category = CharFilter(field_name='category__name', lookup_expr='icontains')

    class Meta:
        model = Product
        fields = ['name', 'category']


class CategoryFilter(FilterSet):
    name = CharFilter(lookup_expr='icontains')

    class Meta:
        model = Category
        fields = ['name']