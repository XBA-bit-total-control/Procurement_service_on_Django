import re

from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.serializers import ValidationError

from .models import User, Shop, ProductInfo, OrderItem, Order


class UserSerializer(serializers.Serializer):
    first_name = serializers.CharField(
        min_length=2,
        max_length=150
    )
    last_name = serializers.CharField(
        min_length=2,
        max_length=150,
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
        check_special_characters = re.findall(r"\W+", value)
        check_numbers = re.findall(r"\d+", value)
        if check_special_characters:
            raise ValidationError(f"The first_name field contains invalid "
                             f"special characters [ {check_special_characters} ]")
        if check_numbers:
            raise ValidationError(f"The first_name field must not contain numbers. "
                             f"Exclude [ {check_numbers} ]")
        return value

    def validate_last_name(self, value):
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
        try:
            validate_password(value)
        except ValidationError as err:
            raise ValidationError(err.detail)
        else:
            return value

    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data['password'])
        return User.objects.create(**validated_data)


class GetUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name',
                  'patronymic', 'is_confirm']


class PutUserSerializer(serializers.Serializer):
    first_name = serializers.CharField(
        min_length=2,
        max_length=150,
        required=False
    )
    last_name = serializers.CharField(
        min_length=2,
        max_length=150,
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
        UserSerializer.validate_first_name(self, value)

    def validate_last_name(self, value):
        UserSerializer.validate_last_name(self, value)

    def validate_patronymic(self, value):
        UserSerializer.validate_patronymic(self, value)


class CustomAuthTokenSerializer(AuthTokenSerializer):
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
                msq = _("Users with an unconfirmed email cannot receive an authentication token. "
                        "Complete the registration by confirming your email.")
                raise ValidationError(msq, code='authorization')
        else:
            msg = _('Must include "email" and "password".')
            raise ValidationError(msg, code='authorization')

        attrs['user'] = user
        return attrs


class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ['id', 'name', 'url']


class ProductInfoSerializer(serializers.ModelSerializer):
    shop_id = serializers.IntegerField(source='shop.id')
    category_id = serializers.IntegerField(source='product.category.id')

    class Meta:
        model = ProductInfo
        fields = ["id", "shop_id", "category_id", "model",
                  "name", "quantity", "price", "price_rrc"]


class PostProductInfoSerializer(serializers.Serializer):
    product_info = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1)


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product_info.name')
    shop_name = serializers.CharField(source='shop.name')
    common_price = serializers.SerializerMethodField()

    def get_common_price(self, obj):
        price = obj.product_info.price
        quantity = obj.quantity
        return price * quantity

    class Meta:
        model = OrderItem
        fields = ["id", "quantity", "product_name", "shop_name", "common_price"]


class PutOrderItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1)


class ContactSerializer(serializers.Serializer):
    telephone = serializers.CharField(
        min_length=11,
        max_length=70,
    )
    settlement = serializers.CharField(
        min_length=3,
        max_length=40,
    )
    street = serializers.CharField(
        min_length=3,
        max_length=70,
    )
    house = serializers.CharField(
        min_length=1,
        max_length=10,
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
        pattern = r"(\+7|8)\s?[- (]?(\d{3})[- )]?\s?[- ]?(\d{3})[- ]?(\d{2})[- ]?(\d{2})\D*(\d{2,5})?"
        check = re.findall(pattern, value)
        error_msg = ("Incorrect telephone value. Please adhere to the format"
                     " +7 999 999 99 99 доб. (2 to 5 digits). The extension is not required.")

        if len(check) == 0:
            raise ValidationError(error_msg)
        parts = check[0]
        if not parts[5]:
            value = f"+7({parts[1]}){parts[2]}-{parts[3]}-{parts[4]}"
        if parts[5]:
            if "доб" in value:
                value = f"+7({parts[1]}){parts[2]}-{parts[3]}-{parts[4]} доб. {parts[5]}"
            else:
                raise ValidationError(error_msg)
        return value

    def validate(self, data):
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
        pattern = r"(\+7|8)\s?[- (]?(\d{3})[- )]?\s?[- ]?(\d{3})[- ]?(\d{2})[- ]?(\d{2})\D*(\d{2,5})?"
        check = re.findall(pattern, value)
        error_msg = ("Incorrect telephone value. Please adhere to the format"
                     " +7 999 999 99 99 доб. (2 to 5 digits). The extension is not required.")

        if len(check) == 0:
            raise ValidationError(error_msg)
        parts = check[0]
        if not parts[5]:
            value = f"+7({parts[1]}){parts[2]}-{parts[3]}-{parts[4]}"
        if parts[5]:
            if "доб" in value:
                value = f"+7({parts[1]}){parts[2]}-{parts[3]}-{parts[4]} доб. {parts[5]}"
            else:
                raise ValidationError(error_msg)
        return value

    def validate(self, data):
        def check_by_regex(key: str, value: str) -> None:
            check = re.findall(r"[0-9а-яА-Яa-zA-Z\s]", value)
            if len(check) != len(value):
                raise ValidationError(f"The field {key} contains invalid characters")

        need_list_not_null = ["settlement", "building", "house"]
        need_list_null = ["flat", "structure", "street"]

        need_data = {key: value for key, value in data.items() if key in need_list_not_null + need_list_null}

        for key, value in need_data.items():
            if key in need_list_null and value is None:
                continue
            check_by_regex(key, value)

        return data


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ["id", "status", "created_at"]


class CategorySerializer(serializers.Serializer):
    id = serializers.IntegerField(min_value=1)
    name = serializers.CharField(
        min_length=2,
        max_length=175,
    )
