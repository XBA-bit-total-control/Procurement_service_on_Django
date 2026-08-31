from django.contrib.auth.models import User
from django.db import models


class UserNew(User):
    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ["id", "username", "email",
                    "date_joined", "last_login"]

    def __str__(self):
        return f"Пользователь {self.username}"


class Shop(models.Model):
    name = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="наименование"
    )
    url = models.URLField(
        unique=True,
        verbose_name="url/имя файла"
    )

    class Meta:
        verbose_name = "Магазин"
        verbose_name_plural = "Магазины"
        ordering = ["id", "name"]

    def __str__(self):
        return f"Магазин {self.name}"


class Category(models.Model):
    name = models.CharField(
        max_length=175,
        unique=True,
        verbose_name="название"
    )
    shops = models.ManyToManyField(
        Shop,
        related_name="category",
        verbose_name="магазины"
    )

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ["id", "name"]

    def __str__(self):
        return f"Категория {self.name}"


class ShopCategory(models.Model):
    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name="shop_category",
        verbose_name="магазин"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="shop_category",
        verbose_name="категория"
    )


class Product(models.Model):
    name = models.CharField(
        max_length=175,
        verbose_name="название"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        verbose_name="категория"
    )

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ["id", "name", "category"]

    def __str__(self):
        return f"Товар {self.name}"


class ProductInfo(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name="товар"
    )
    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        verbose_name="магазин"
    )
    name = models.CharField(
        max_length=255,
        verbose_name="название"
    )
    quantity = models.PositiveIntegerField(
        verbose_name="количество"
    )
    price = models.DecimalField(
        max_digits=11,
        decimal_places=2,
        verbose_name="стоимость"
    )
    price_rrc = models.DecimalField(
        max_digits=11,
        decimal_places=2,
        null=True,
        verbose_name="РРЦ"
    )

    class Meta:
        verbose_name = "Информация о товаре"
        verbose_name_plural = "Информация о товарах"
        ordering = ["id", "name", "quantity", "price",
                    "price_rrc", "shop", "product"]

    def __str__(self):
        return f"Товар {self.name}"


class Parameter(models.Model):
    name = models.CharField(
        max_length=255,
        verbose_name="именование"
    )

    class Meta:
        verbose_name = "Параметр"
        verbose_name_plural = "Параметры"
        ordering = ["id", "name"]

    def __str__(self):
        return f"Параметр {self.name}"


class ProductParameter(models.Model):
    product_info = models.ForeignKey(
        ProductInfo,
        on_delete=models.CASCADE,
        verbose_name="информация о товаре"
    )
    parameter = models.ForeignKey(
        Parameter,
        on_delete=models.CASCADE,
        verbose_name="параметр"
    )
    value = models.CharField(
        max_length=105,
        verbose_name="значение"
    )

    class Meta:
        verbose_name = "Значение параметра"
        verbose_name_plural = "Значения параметров"
        ordering = ["id", "parameter", "value"]

    def __str__(self):
        return f"Значения для товара {self.product_info.name}"


class Order(models.Model):
    STATUS_CHOICES = {
        "PROCESSING": "в обработке",
        "GETTING_READY": "собирается",
        "ON_THE_WAY": "доставляется",
        "DELIVERED": "доставлен",
        "RETURNED": "возвращен",
        "CANCELED": "отменен",
        "ERROR": "ошибка"
    }
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="пользователь"
    )
    created_at = models.DateTimeField(
        auto_now=True,
        verbose_name="создано"
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default="PROCESSING"
    )

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ["id", "created_at", "status"]

    def __str__(self):
        return f"Заказ №{self.id}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        verbose_name="заказ"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name="товар"
    )
    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        verbose_name="магазин"
    )
    quantity = models.PositiveIntegerField(
        verbose_name="количество"
    )

    class Meta:
        verbose_name = "Товар в заказе"
        verbose_name_plural = "Товары в заказе"
        ordering = ["id", "product", "shop", "quantity"]

    def __str__(self):
        return f"Товар для заказа №{self.order.id}"


class Contact(models.Model):
    TYPE_CHOICES = {
        "TELEPHONE": "Телефон",
        "ADDRESS": "Адрес"
    }
    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        verbose_name="тип"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="пользователь"
    )
    value = models.TextField(
        verbose_name="значение"
    )

    class Meta:
        verbose_name = "Контакт"
        verbose_name_plural = "Контакты"
        ordering = ["id", "type", "user", "value"]

    def __str__(self):
        return f"Контакт пользователя {self.user.username}"
