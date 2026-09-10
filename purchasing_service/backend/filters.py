import django_filters

from .models import User, Shop


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
