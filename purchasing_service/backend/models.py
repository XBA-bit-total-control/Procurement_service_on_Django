from django.contrib.auth.models import BaseUserManager, AbstractUser
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """
    Пользовательский класс-менеджер для модели User.
    Определены методы создания обычного пользователя и администратора.
    Использование username заменено на email.
    """
    def create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_staff", True)
        if not extra_fields.get("is_staff"):
            raise ValueError("The superuser must be an employee")
        if not extra_fields.get("is_superuser"):
            raise ValueError("The superuser must be such")

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Кастомная модель для пользователя.

    Аутентификация заменена на использование email вместо username.
    При создании суперпользователя обязательными полями назначены:
        email, first_name, last_name и password.

    Attributes:
        first_name: имя пользователя
        last_name: фамилия
        email: электронная почта
        patronymic: отчество
        is_shop: является ли пользователь магазином
        is_confirm: подтвержден ли пользователь по email
        is_active: активен ли профиль пользователя
        is_staff: является ли пользователь сотрудником
        is_superuser: является ли суперпользователем

    Notes:
        Поле username удалено и в качестве указания имени используется firs_name.
        Поле password не объявляется, но присутствует в модели.
    """
    first_name = models.CharField(
        max_length=150,
        verbose_name="имя"
    )
    last_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="фамилия"
    )
    email = models.EmailField(
        unique=True,
        verbose_name="email"
    )
    patronymic = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="отчество"
    )
    is_shop = models.BooleanField(
        default=False,
        verbose_name="магазин"
    )
    is_confirm = models.BooleanField(
        default=False,
        null=True,
        blank=True,
        verbose_name="подтвержденный"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="активен"
    )
    is_staff = models.BooleanField(
        default=False,
        verbose_name="работник"
    )
    is_superuser = models.BooleanField(
        default=False,
        verbose_name="администратор"
    )
    username = None

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        verbose_name = "пользователь"
        verbose_name_plural = "пользователи"
        ordering = ["id"]

    def __str__(self):
        return self.first_name


class Shop(models.Model):
    """Модель магазина.

    Определяет магазин с принадлежностью к пользователю.

    Attributes:
        user: связь с пользователем
        name: наименование
        url: ссылка
        status: статус приёма заказов

    Note:
        В STATUS_CHOICES доступные статусы для магазина.
    """
    STATUS_CHOICES = (
        ("ACCEPT_ORDERS", "принимаю заказы"),
        ("NOT_ACCEPT_ORDERS", "не принимаю заказы")
    )
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="shop",
        verbose_name="пользователь"
    )
    name = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="наименование"
    )
    url = models.URLField(
        unique=True,
        null=True,
        blank=True,
        verbose_name="url"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="ACCEPT_ORDERS",
        verbose_name="статус"
    )

    class Meta:
        verbose_name = "Магазин"
        verbose_name_plural = "Магазины"
        ordering = ["id", "name"]

    def __str__(self):
        return self.name


class Category(models.Model):
    """Модель категории.

    Определяет категорию с принадлежностью к магазину.
    Связана с магазином через промежуточную модель ShopCategory.

    Attributes:
        name: название
        shops: связь с магазинами
    """
    name = models.CharField(
        max_length=175,
        unique=True,
        verbose_name="название"
    )
    shops = models.ManyToManyField(
        Shop,
        through="ShopCategory",
        verbose_name="магазины"
    )

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ["id", "name"]

    def __str__(self):
        return self.name


class ShopCategory(models.Model):
    """Связующая модель Магазин-Категория.

    Обеспечивает явную связь многие-ко-многим.

    Attributes:
        shop: связь с магазином
        category: связь с категорией
    """
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

    class Meta:
        verbose_name = "Связь Магазин-Категория"
        verbose_name_plural = "Связи Магазины-Категории"
        ordering = ["id"]


class Product(models.Model):
    """Модель товара.

    Определяет товар с принадлежностью к категории.

    Attributes:
        name: название
        category: связь с категорией
    """
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
        return self.name


class ProductInfo(models.Model):
    """Модель информации о товаре.

    Определяет расширенную информацию о товаре в магазине.

    Attributes:
        product: связь с товаром
        shop: связь с магазином
        model: модель
        name: название
        quantity: количество единиц
        price: стоимость
        price_rrc: розничная стоимость
    """
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
    model = models.CharField(
        max_length=255,
        verbose_name="модель",
        default="not_specified",
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
        blank=True,
        verbose_name="РРЦ"
    )

    class Meta:
        verbose_name = "Информация о товаре"
        verbose_name_plural = "Информация о товарах"
        ordering = ["id", "name", "quantity", "price",
                    "price_rrc", "shop", "product"]

    def __str__(self):
        return self.name


class Parameter(models.Model):
    """Модель параметра товаров.

    Определяет наименование параметра.

    Attributes:
        name: наименование
    """
    name = models.CharField(
        max_length=255,
        verbose_name="именование"
    )

    class Meta:
        verbose_name = "Параметр"
        verbose_name_plural = "Параметры"
        ordering = ["id", "name"]

    def __str__(self):
        return self.name


class ProductParameter(models.Model):
    """Модель значения параметра для товара.

    Связывает информацию о товаре с параметром и хранит значение.

    Attributes:
        product_info: связь с информацией о товаре
        parameter: связь с параметром
        value: значение
    """
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
    """Модель заказа.

    Заказ со статусом NOT_CREATED является корзиной пользователя.

    Attributes:
        user: пользователь
        created_at: дата создания
        status: статус

    Note:
        STATUS_CHOICES определяет доступные статусы.
    """
    STATUS_CHOICES = (
        ("NOT_CREATED", "не создан"),
        ("PROCESSING", "в обработке"),
        ("GETTING_READY", "собирается"),
        ("ON_THE_WAY", "доставляется"),
        ("DELIVERED", "доставлен"),
        ("RETURNED", "возвращен"),
        ("CANCELED", "отменен"),
        ("ERROR", "ошибка")
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="пользователь"
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="создано"
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default="NOT_CREATED",
        verbose_name="статус"
    )
    contact = models.ForeignKey(
        "Contact",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="контакты"
    )

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ["id", "created_at", "status"]

    def __str__(self):
        return f"№ {self.id}"


class OrderItem(models.Model):
    """Модель содержимого заказа/корзины.

    Обеспечивает указание товаров в заказе/корзине и их количество.

    Attributes:
        order: связь с заказом
        product_info: связь с информацией о товаре
        shop: связь с магазином
        quantity: количество единиц товара
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        verbose_name="заказ"
    )
    product_info = models.ForeignKey(
        ProductInfo,
        on_delete=models.CASCADE,
        verbose_name="информация о товаре"
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
        ordering = ["id", "product_info", "shop", "quantity"]

    def __str__(self):
        return f"Товар для заказа №{self.order.id}"


class Contact(models.Model):
    """Модель контактов пользователя.

    Определяет контакты пользователя для оформления заказа.

    Attributes:
        user: связь с пользователем
        telephone: номер телефона
        settlement: поселение
        street: улица
        house: дом
        structure: строение
        building: корпус
        flat: квартира
        comment: комментарий
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="пользователь"
    )
    telephone = models.CharField(
        max_length=70,
        verbose_name="номер телефона"
    )
    settlement = models.CharField(
        max_length=40,
        verbose_name="поселение"
    )
    street = models.CharField(
        max_length=70,
        verbose_name="улица"
    )
    house = models.CharField(
        max_length=10,
        verbose_name="дом"
    )
    structure = models.CharField(
        max_length=10,
        verbose_name="строение",
        null=True,
        blank=True
    )
    building = models.CharField(
        max_length=10,
        verbose_name="корпус",
        null=True,
        blank=True
    )
    flat = models.CharField(
        max_length=10,
        verbose_name="квартира",
        null=True,
        blank=True
    )
    comment = models.CharField(
        max_length=90,
        verbose_name="комментарий",
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = "Контакт"
        verbose_name_plural = "Контакты"
        ordering = ["id"]

    def __str__(self):
        return f"№ {self.id}"


class ConfirmationTokens(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        verbose_name="пользователь"
    )
    token_for_email = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        default=None,
        verbose_name="токен регистрации"
    )
    token_for_partner = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        default=None,
        verbose_name="токен партнёрства"
    )

    class Meta:
        verbose_name = "Токен подтверждения"
        verbose_name_plural = "Токены подтверждения"
        ordering = ["id"]

    def __str__(self):
        return f"{self.id}"
