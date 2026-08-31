from django.contrib import admin

from .models import *


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "url"]
    list_filter = ["id", "name"]


class ShopCategoryInline(admin.TabularInline):
    model = ShopCategory
    extra = 3


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["id", "name"]
    list_filter = ["id", "name"]
    inlines = [ShopCategoryInline, ]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "category"]
    list_filter = ["id", "name", "category"]


@admin.register(ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    list_display = ["id", "product", "shop", "name",
                    "quantity", "price", "price_rrc"]
    list_filter = ["id", "name", "quantity", "price",
                   "price_rrc", "shop", "product"]


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    list_display = ["id", "name"]
    list_filter = ["id", "name"]


@admin.register(ProductParameter)
class ProductParameterAdmin(admin.ModelAdmin):
    list_display = ["id", "product_info", "parameter", "value"]
    list_filter = ["id", "parameter", "value"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "created_at", "status"]
    list_filter = ["id", "user", "created_at", "status"]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ["id", "product", "shop", "quantity"]
    list_filter = ["id", "product", "shop", "quantity"]


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ["id", "type", "user", "value"]
    list_filter = ["id", "type", "user", "value"]
