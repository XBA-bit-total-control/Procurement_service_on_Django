from django.contrib import admin

from .models import (Shop, ShopCategory, Category, Product,
                     ProductInfo, Parameter, ProductParameter,
                     Order, OrderItem, Contact, User,
                     ConfirmationTokens)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Представление модели User в админке."""

    list_display = ["id", "first_name", "last_name", "patronymic",
                    "email", "is_active", "is_shop",
                    "is_confirm", "is_staff", "is_superuser"]
    list_filter = ["id", "first_name", "last_name", "patronymic",
                   "email", "is_active", "is_shop",
                   "is_confirm", "is_staff", "is_superuser"]
    search_fields = ["id", "first_name", "last_name",
                     "patronymic", "email"]
    ordering = ["id"]


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    """Представление модели Shop в админке."""

    list_display = ["id", "name", "url", "user", "status"]
    list_filter = ["name"]
    search_fields = ["name", "url", "user__email"]
    ordering = ["id"]


class ShopCategoryInline(admin.TabularInline):
    """
    Класс добавляющий специализированные поля при создании категории
    для установки связей с магазинами.
    """
    model = ShopCategory
    extra = 3


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Представление модели Category в админке."""

    list_display = ["id", "name"]
    list_filter = ["id", "name"]
    search_fields = ["id", "name"]
    ordering = ["id"]
    inlines = [ShopCategoryInline, ]


@admin.register(ShopCategory)
class ShopCategoryAdmin(admin.ModelAdmin):
    """Представление связующей модели ShopCategory в админке."""

    list_display = ["id", "shop", "category"]
    list_filter = ["id", "shop", "category"]
    search_fields = ["id"]
    ordering = ["id"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Представление модели Product в админке."""

    list_display = ["id", "name", "category"]
    list_filter = ["id", "name", "category"]
    search_fields = ["id", "name"]
    ordering = ["id"]


@admin.register(ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    """Представление модели ProductInfo в админке."""

    list_display = ["id", "product", "shop", "name",
                    "quantity", "price", "price_rrc",
                    "is_deleted"]
    list_filter = ["id", "product", "shop", "name",
                   "quantity", "price", "price_rrc",
                   "is_deleted"]
    search_fields = ["id", "name", "quantity",
                     "price", "price_rrc"]
    ordering = ["id"]


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    """Представление модели Parameter в админке."""

    list_display = ["id", "name"]
    list_filter = ["id", "name"]
    search_fields = ["id", "name"]
    ordering = ["id"]


@admin.register(ProductParameter)
class ProductParameterAdmin(admin.ModelAdmin):
    """Представление модели ProductParameter в админке."""

    list_display = ["id", "product_info", "parameter", "value"]
    list_filter = ["id", "product_info", "parameter", "value"]
    search_fields = ["id", "value"]
    ordering = ["id"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Представление модели Order в админке."""

    list_display = ["id", "user", "created_at", "status", "contact"]
    list_filter = ["id", "user", "created_at", "status", "contact"]
    search_fields = ["id", "created_at", "status"]
    ordering = ["id"]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """Представление модели OrderItem в админке."""

    list_display = ["id", "order", "product_info", "shop", "quantity"]
    list_filter = ["id", "order", "product_info", "shop", "quantity"]
    search_fields = ["id", "quantity"]
    ordering = ["id"]


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    """Представление модели Contact в админке."""

    list_display = ["id", "user", "telephone", "settlement", "street",
                    "house", "structure", "building", "flat", "comment"]
    list_filter = ["id", "user", "telephone", "settlement", "street",
                   "house", "structure", "building", "flat"]
    search_fields = ["id", "telephone", "settlement", "street",
                     "house", "structure", "building", "flat", "comment"]
    ordering = ["id"]


@admin.register(ConfirmationTokens)
class ConfirmationTokensAdmin(admin.ModelAdmin):
    """Представление модели ConfirmationTokens в админке."""

    list_display = ["id", "user", "token_for_email", "token_for_partner"]
    list_filter = ["id", "user"]
    search_fields = ["id", "token_for_email", "token_for_partner"]
    ordering = ["id"]
