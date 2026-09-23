import re

from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.serializers import ValidationError

from .models import User, ProductInfo, OrderItem, Order


class UserSerializer(serializers.Serializer):
    """Сериализатор для кастомной модели пользователя.

    Для всех полей кроме email определены валидаторы.

    Attributes:
        first_name: имя
        last_name: фамилия
        patronymic: отчество
        email: электронная почта
        password: пароль

    Note:
        Для хэширования пароля переопределен метод create.
    """
    first_name = serializers.CharField(
        min_length=2,
        max_length=150
    )
    last_name = serializers.CharField(
        min_length=2,
        max_length=255,
        allow_null=True,
        required=False,
        default=None
    )
    patronymic = serializers.CharField(
        min_length=2,
        max_length=255,
        allow_null=True,
        required=False,
        default=None
    )
    email = serializers.EmailField()
    password = serializers.CharField(
        min_length=8,
        max_length=108,
        write_only=True
    )

    def validate_first_name(self, value):
        """Валидатор имени пользователя.

        Допускает использование только букв и подчеркивания.
        """
        check_special_characters = re.findall(r"\W+", value)
        check_numbers = re.findall(r"\d+", value)
        if check_special_characters:
            raise ValidationError(f"The first_name field contains invalid "
                                  f"special characters [ {' '.join(check_special_characters)} ]")
        if check_numbers:
            raise ValidationError(f"The first_name field must not contain numbers. "
                                  f"Exclude [ {' '.join(check_numbers)} ]")
        return value

    def validate_last_name(self, value):
        """Валидатор фамилии пользователя.

        Допускает использование только букв и подчеркивания.
        """
        if value is None:
            return value
        check_special_characters = re.findall(r"\W+", value)
        check_numbers = re.findall(r"\d+", value)
        if check_special_characters:
            raise ValidationError(f"The last_name field contains invalid "
                                  f"special characters [ {' '.join(check_special_characters)} ]")
        if check_numbers:
            raise ValidationError(f"The last_name field must not contain numbers. "
                                  f"Exclude [ {' '.join(check_numbers)} ]")
        return value

    def validate_patronymic(self, value):
        """Валидатор отчества пользователя.

        Допускает использование только букв и подчеркивания.
        """
        if value is None:
            return value
        check_special_characters = re.findall(r"\W+", value)
        check_numbers = re.findall(r"\d+", value)
        if check_special_characters:
            raise ValidationError(f"The patronymic field contains invalid "
                                  f"special characters [ {' '.join(check_special_characters)} ]")
        if check_numbers:
            raise ValidationError(f"The patronymic field must not contain numbers. "
                                  f"Exclude [ {' '.join(check_numbers)} ]")
        return value

    def validate_password(self, value):
        """Валидация пароля с помощью функции django."""

        validate_password(value)
        return value

    def create(self, validated_data):
        """Создание пользователя с хэшированием пароля."""

        validated_data['password'] = make_password(validated_data['password'])
        return User.objects.create(**validated_data)


class GetUserSerializer(serializers.ModelSerializer):
    """Отдельный сериализатор пользователей для GET-запроса.

    Возвращает поля доступные всем пользователям для просмотра.
    """

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name',
                  'patronymic', 'is_confirm']


class PutUserSerializer(serializers.Serializer):
    """Отдельный сериализатор пользователей для PUT-запроса.

    В отличие от UserSerializer, не имеет поля password, так как
    через PUT-запрос нельзя сменить пароль.

    Note:
        Использует валидаторы из UserSerializer.
    """
    first_name = serializers.CharField(
        min_length=2,
        max_length=150,
        required=False
    )
    last_name = serializers.CharField(
        min_length=2,
        max_length=255,
        required=False,
        allow_null=True
    )
    patronymic = serializers.CharField(
        min_length=2,
        max_length=255,
        required=False,
        allow_null=True
    )
    email = serializers.EmailField(required=False)

    def validate_first_name(self, value):
        return UserSerializer.validate_first_name(self, value)

    def validate_last_name(self, value):
        return UserSerializer.validate_last_name(self, value)

    def validate_patronymic(self, value):
        return UserSerializer.validate_patronymic(self, value)


class CustomAuthTokenSerializer(AuthTokenSerializer):
    """Кастомный сериализатор для аутентификации пользователей по email и password."""

    username = None
    email = serializers.EmailField()

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(request=self.context.get('request'),
                                email=email, password=password)
            if not user:
                msg = _('Unable to log in with provided credentials. '
                        'Check the spelling of the email and password.')
                raise ValidationError(msg, code='authorization')

            if not user.is_confirm:
                msg = _("Users with an unconfirmed email cannot receive an authentication token. "
                        "Complete the registration by confirming your email.")
                raise ValidationError(msg, code='authorization')

            if not user.is_active:
                msg = _("An inactive user cannot receive a token")
                raise ValidationError(msg, code='authorization')
        else:
            msg = _('Must include "email" and "password".')
            raise ValidationError(msg, code='authorization')

        attrs['user'] = user
        return attrs


class ShopSerializer(serializers.Serializer):
    """Сериализатор для модели магазина.

    Attributes:
        id: идентификатор
        name: название
        url: ссылка
    """
    id = serializers.IntegerField(
        min_value=1,
        required=False
    )
    name = serializers.CharField(
        min_length=3,
        max_length=255
    )
    url = serializers.URLField(
        allow_null=True,
        required=False
    )


class ProductInfoSerializer(serializers.ModelSerializer):
    """Сериализатор для информации о товаре.

    Для информативности имеет дополнительные поля.

    Attributes:
        product_id: идентификатор товара
        shop_id: идентификатор магазина
        category_id: идентификатор категории
    """
    product_id = serializers.IntegerField(source='product.id')
    shop_id = serializers.IntegerField(source='shop.id')
    category_id = serializers.IntegerField(source='product.category.id')

    class Meta:
        model = ProductInfo
        fields = ["id", "product_id", "shop_id", "category_id", "model",
                  "name", "quantity", "price", "price_rrc"]


class PostProductInfoSerializer(serializers.Serializer):
    """Отдельный сериализатор информации о товаре.

    Создан для добавления товара в корзину.

    Attributes:
        product_info: идентификатор товара
        quantity: количество
    """
    product_info = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1)


class OrderItemSerializer(serializers.ModelSerializer):
    """Сериализатор для информации о товаре в заказе/корзине.

    Attributes:
        product_name: название товара
        shop_name: название магазина
        common_price: общая цена товара
    """
    product_name = serializers.CharField(source='product_info.name')
    shop_name = serializers.CharField(source='shop.name')
    common_price = serializers.SerializerMethodField()

    def get_common_price(self, obj):
        """Метод подсчета общей стоимости товара."""

        price = obj.product_info.price
        quantity = obj.quantity
        return price * quantity

    class Meta:
        model = OrderItem
        fields = ["id", "quantity", "product_name", "shop_name", "common_price"]


class PutOrderItemSerializer(serializers.Serializer):
    """Отдельный сериализатор для информации о товаре в заказе/корзине для PUT-запроса.

    Attributes:
        id: идентификатор
        quantity: количество
    """
    id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1)


class ContactSerializer(serializers.Serializer):
    """Сериализатор для контактов пользователей.

    Для всех полей кроме телефона и комментария допускается использование только букв и цифр.

    Attributes:
        id: идентификатор
        telephone: номер телефона
        settlement: населенный пункт
        street: улица
        house: номер дома
        structure: строение
        building: корпус
        flat: квартира
        comment: комментарий

    Note:
        Телефон валидируется и преобразуется к формату +7 999 999-99-99 доб. (2 to 5 digits).
        Добавочный номер указывается при наличии.
    """
    id = serializers.IntegerField(required=False)
    telephone = serializers.CharField(
        min_length=11,
        max_length=70
    )
    settlement = serializers.CharField(
        min_length=3,
        max_length=40
    )
    street = serializers.CharField(
        min_length=3,
        max_length=70
    )
    house = serializers.CharField(
        min_length=1,
        max_length=10
    )
    structure = serializers.CharField(
        min_length=1,
        max_length=10,
        allow_null=True,
        required=False
    )
    building = serializers.CharField(
        min_length=1,
        max_length=10,
        allow_null=True,
        required=False
    )
    flat = serializers.CharField(
        min_length=1,
        max_length=10,
        allow_null=True,
        required=False
    )
    comment = serializers.CharField(
        min_length=10,
        max_length=90,
        allow_null=True,
        required=False
    )

    def validate_telephone(self, value):
        """Валидатор для номера телефона.

        Валидны лишь номера начинающиеся с +7 или 8.
        """
        pattern = r"(\+7|8)\s?[- (]?(\d{3})[- )]?\s?[- ]?(\d{3})[- ]?(\d{2})[- ]?(\d{2})\D*(\d{2,5})?"
        check = re.findall(pattern, value)
        error_msg = ("Incorrect telephone value. Please adhere to the format"
                     " +7 999 999 99 99 доб. (2 to 5 digits). The extension is not required.")

        if len(check) == 0:
            raise ValidationError(error_msg)
        parts = check[0]
        if not parts[5]:
            value = f"+7({parts[1]}){parts[2]}-{parts[3]}-{parts[4]}"
        else:
            if "доб" in value:
                value = f"+7({parts[1]}){parts[2]}-{parts[3]}-{parts[4]} доб. {parts[5]}"
            else:
                raise ValidationError(error_msg)
        return value

    def validate(self, data):
        """Валидатор для значений адреса."""

        def check_by_regex(key: str, value: str) -> None:
            check = re.findall(r"[0-9а-яА-Яa-zA-Z\s]", value)
            if len(check) != len(value):
                raise ValidationError(f"The field {key} contains invalid characters")

        need_list = ["settlement", "street", "house",
                     "structure", "building", "flat"]

        need_data = {key: value for key, value in data.items() if key in need_list}

        for key, value in need_data.items():
            check_by_regex(key, value)

        return data


class PutContactSerializer(serializers.Serializer):
    """Отдельный сериализатор для контактов пользователей при PUT-запросе.

    Attributes:
        id: идентификатор
        telephone: номер телефона
        settlement: населенный пункт
        street: улица
        house: номер дома
        structure: строение
        building: корпус
        flat: квартира
        comment: комментарий

    Note:
        Для валидации используются валидаторы из ContactSerializer.
    """
    id = serializers.IntegerField(
        min_value=1,
        required=True
    )
    telephone = serializers.CharField(
        min_length=11,
        max_length=70,
        required=False
    )
    settlement = serializers.CharField(
        min_length=3,
        max_length=40,
        required=False
    )
    street = serializers.CharField(
        min_length=3,
        max_length=70,
        required=False
    )
    house = serializers.CharField(
        min_length=1,
        max_length=10,
        required=False
    )
    structure = serializers.CharField(
        min_length=1,
        max_length=10,
        allow_null=True,
        required=False
    )
    building = serializers.CharField(
        min_length=1,
        max_length=10,
        allow_null=True,
        required=False
    )
    flat = serializers.CharField(
        min_length=1,
        max_length=10,
        allow_null=True,
        required=False
    )
    comment = serializers.CharField(
        min_length=10,
        max_length=90,
        allow_null=True,
        required=False
    )

    def validate_telephone(self, value):
        return ContactSerializer.validate_telephone(self, value)

    def validate(self, data):
        return ContactSerializer.validate(self, data)


class OrderSerializer(serializers.ModelSerializer):
    """Сериализатор для заказов."""

    class Meta:
        model = Order
        fields = ["id", "status", "created_at"]


class CategorySerializer(serializers.Serializer):
    """Сериализатор категорий.

    Attributes:
        id: идентификатор
        name: название
    """
    id = serializers.IntegerField(min_value=1)
    name = serializers.CharField(
        min_length=2,
        max_length=175
    )


class PartnerOrderItemSerializer(serializers.ModelSerializer):
    """Сериализатор содержания товаров в заказе для партнеров.

    Возвращает детальную информацию о созданном заказе.

    Attributes:
        status: статус заказа
        product_name: название товара
        quantity: количество товара в заказе
        order_id: идентификатор заказа
        product_info_id: идентификатор информации о товаре
        contacts: контакты пользователя

    Note:
        Для подробной информации контактов используется ContactSerializer.
    """
    status = serializers.CharField(source='order.status')
    product_name = serializers.CharField(source='product_info.name')
    quantity = serializers.IntegerField(min_value=1)
    order_id = serializers.IntegerField(source='order.id')
    product_info_id = serializers.IntegerField(source='product_info.id')
    contacts = ContactSerializer(
        source='order.contact',
        read_only=True
    )

    class Meta:
        model = OrderItem
        fields = ["status", "product_name", "quantity",
                  "order_id", "product_info_id", "contacts"]
