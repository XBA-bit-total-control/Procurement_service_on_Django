import django_filters

from .models import User, Shop, Category, ProductInfo


class UserFilter(django_filters.FilterSet):
    id = django_filters.NumberFilter(field_name='id')

    name = django_filters.CharFilter(field_name='first_name')
    name_contains = django_filters.CharFilter(
        field_name='first_name',
        lookup_expr='contains'
    )

    last_name = django_filters.CharFilter(field_name='last_name')
    last_name_contains = django_filters.CharFilter(
        field_name='last_name',
        lookup_expr='contains'
    )

    patronymic = django_filters.CharFilter(field_name='patronymic')
    patronymic_contains = django_filters.CharFilter(
        field_name='patronymic',
        lookup_expr='contains'
    )

    email = django_filters.CharFilter(field_name='email')

    class Meta:
        model = User
        fields = []


class ShopFilter(django_filters.FilterSet):
    id = django_filters.NumberFilter(field_name='id')

    name = django_filters.CharFilter(field_name='name')
    name_contains = django_filters.CharFilter(
        field_name='name',
        lookup_expr='contains'
    )

    url = django_filters.CharFilter(field_name='url')
    url_contains = django_filters.CharFilter(
        field_name='url',
        lookup_expr='contains'
    )
    no_url = django_filters.BooleanFilter(
        field_name='url',
        lookup_expr='isnull',
    )

    class Meta:
        model = Shop
        fields = []


class CategoryFilter(django_filters.FilterSet):
    id = django_filters.NumberFilter(field_name='id')

    name = django_filters.CharFilter(field_name='name')
    name_contains = django_filters.CharFilter(
        field_name='name',
        lookup_expr='contains'
    )

    class Meta:
        model = Category
        fields = []


class ProductInfoFilter(django_filters.FilterSet):
    id = django_filters.NumberFilter(field_name='id')
    product_id = django_filters.NumberFilter(field_name='product_id')
    shop_id = django_filters.NumberFilter(field_name='shop_id')
    category_id = django_filters.NumberFilter(field_name='product__category_id')

    model = django_filters.CharFilter(field_name='model')
    model_contains = django_filters.CharFilter(
        field_name='model',
        lookup_expr='contains'
    )

    name = django_filters.CharFilter(field_name='name')
    name_contains = django_filters.CharFilter(
        field_name='name',
        lookup_expr='contains'
    )

    quantity = django_filters.NumberFilter(field_name='quantity')
    quantity_less = django_filters.NumberFilter(
        field_name='quantity',
        lookup_expr='lt'
    )
    quantity_more = django_filters.NumberFilter(
        field_name='quantity',
        lookup_expr='gt'
    )

    price = django_filters.NumberFilter(field_name='price')
    price_less = django_filters.NumberFilter(
        field_name='price',
        lookup_expr='lt'
    )
    price_more = django_filters.NumberFilter(
        field_name='price',
        lookup_expr='gt'
    )

    price_rrc = django_filters.NumberFilter(field_name='price_rrc')
    price_rrc_less = django_filters.NumberFilter(
        field_name='price_rrc',
        lookup_expr='lt'
    )
    price_rrc_more = django_filters.NumberFilter(
        field_name='price_rrc',
        lookup_expr='gt'
    )

    class Meta:
        model = ProductInfo
        fields = []
