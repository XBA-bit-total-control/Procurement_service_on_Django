import re

from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.serializers import ValidationError

from .models import User


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
                             f"special characters {check_special_characters}")
        if check_numbers:
            raise ValidationError(f"The first_name field must not contain numbers. "
                             f"Exclude {check_numbers}")
        return value

    def validate_last_name(self, value):
        if value is None:
            return value
        check_special_characters = re.findall(r"\W+", value)
        check_numbers = re.findall(r"\d+", value)
        if check_special_characters:
            raise ValidationError(f"The last_name field contains invalid "
                             f"special characters [{' '.join(check_special_characters)}]")
        if check_numbers:
            raise ValidationError(f"The last_name field must not contain numbers. "
                             f"Exclude [{' '.join(check_numbers)}]")
        return value

    def validate_patronymic(self, value):
        if value is None:
            return value
        check_special_characters = re.findall(r"\W+", value)
        check_numbers = re.findall(r"\d+", value)
        if check_special_characters:
            raise ValidationError(f"The patronymic field contains invalid "
                             f"special characters [{' '.join(check_special_characters)}]")
        if check_numbers:
            raise ValidationError(f"The patronymic field must not contain numbers. "
                             f"Exclude [{' '.join(check_numbers)}]")
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
