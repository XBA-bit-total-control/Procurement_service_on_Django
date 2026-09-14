from django.contrib import admin

from .models import (Shop, ShopCategory, Category, Product,
                     ProductInfo, Parameter, ProductParameter,
                     Order, OrderItem, Contact, User)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["id", "first_name", "last_name", "patronymic",
                    "email", "registration_token", "is_active", "is_shop",
                    "is_confirm", "is_staff", "is_superuser"]
    list_filter = ["id", "first_name", "last_name", "patronymic",
                    "email", "is_active", "is_shop",
                    "is_confirm", "is_staff", "is_superuser"]
    search_fields = ["id", "first_name", "last_name",
                     "patronymic", "email"]
    ordering = ["id"]


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "url", "user", "status"]
    list_filter = ["id", "name"]
    search_fields = ["id", "name", "url", "user"]
    ordering = ["id"]


class ShopCategoryInline(admin.TabularInline):
    model = ShopCategory
    extra = 3


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["id", "name"]
    list_filter = ["id", "name"]
    search_fields = ["id", "name"]
    ordering = ["id"]
    inlines = [ShopCategoryInline, ]


@admin.register(ShopCategory)
class ShopCategoryAdmin(admin.ModelAdmin):
    list_display = ["id", "shop", "category"]
    list_filter = ["id", "shop", "category"]
    search_fields = ["id"]
    ordering = ["id"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "category"]
    list_filter = ["id", "name", "category"]
    search_fields = ["id", "name"]
    ordering = ["id"]


@admin.register(ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    list_display = ["id", "product", "shop", "name",
                    "quantity", "price", "price_rrc"]
    list_filter = ["id", "product", "shop", "name",
                   "quantity", "price", "price_rrc"]
    search_fields = ["id", "name", "quantity",
                     "price", "price_rrc"]
    ordering = ["id"]


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    list_display = ["id", "name"]
    list_filter = ["id", "name"]
    search_fields = ["id", "name"]
    ordering = ["id"]


@admin.register(ProductParameter)
class ProductParameterAdmin(admin.ModelAdmin):
    list_display = ["id", "product_info", "parameter", "value"]
    list_filter = ["id", "product_info", "parameter", "value"]
    search_fields = ["id", "value"]
    ordering = ["id"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "created_at", "status"]
    list_filter = ["id", "user", "created_at", "status"]
    search_fields = ["id", "created_at", "status"]
    ordering = ["id"]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ["id", "order", "product_info", "shop", "quantity"]
    list_filter = ["id", "order", "product_info", "shop", "quantity"]
    search_fields = ["id", "quantity"]
    ordering = ["id"]


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "telephone", "settlement", "street",
                    "house", "structure", "building", "flat", "comment"]
    list_filter = ["id", "user", "telephone", "settlement", "street",
                   "house", "structure", "building", "flat"]
    search_fields = ["id", "telephone", "settlement", "street",
                     "house", "structure", "building", "flat", "comment"]
    ordering = ["id"]
