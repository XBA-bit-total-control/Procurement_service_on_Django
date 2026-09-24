import re
from random import choice

from rest_framework.serializers import ValidationError

from .models import User


def get_email_random_admin() -> str:
    """Функция для получения электронной почты получения случайного сотрудника.

    Returns:
        str: Почта случайного сотрудника или пустая строка.
    """
    try:
        admins = User.objects.filter(is_staff=True).all()
        return choice(admins).email
    except IndexError:
        print("WARNING: THERE IS NO EMPLOYEE IN THE DATABASE - CREATE AT LEAST ONE")
        return ""


def get_email_random_activ_admin() -> str:
    """Функция для получения электронной почты случайного активного сотрудника.

    Returns:
        str: Почта случайного активного сотрудника или пустая строка.
    """
    try:
        admins = User.objects.filter(is_staff=True, is_active=True).all()
        return choice(admins).email
    except IndexError:
        return get_email_random_admin()


def get_email_random_superuser() -> str:
    """Функция для получения электронной почты случайного администратора.

    Returns:
        str: Почта случайного администратора или пустая строка.
    """
    try:
        superusers = User.objects.filter(is_superuser=True).all()
        return choice(superusers).email
    except IndexError:
        print("WARNING: THERE IS NO ADMINISTRATOR IN THE DATABASE - CREATE AT LEAST ONE")
        return ""


def validate_fio(value):
    """Валидатор для ФИО.

    Допускается использование только букв, дефисов и пробелов.
    """
    check_allowed_characters = re.findall(r"[а-яА-Яa-zA-Z\s-]", value)
    if len(check_allowed_characters) != len(value):
        prohibited_characters = []
        for char in value:
            if char not in check_allowed_characters:
                prohibited_characters.append(char)
        raise ValidationError(f"The first_name field contains invalid "
                              f"special characters [ {' '.join(prohibited_characters)} ]")
    else:
        set_allowed_characters = set(check_allowed_characters)
        set_allowed_characters.discard(" ")
        set_allowed_characters.discard("-")
        if len(set_allowed_characters) == 0:
            raise ValidationError("The value must contain letters")
        return value


def validate_telephone_number(value):
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


def validate_address_values(data):
    """Валидатор для значений адреса."""

    def check_by_regex(key: str, value: str) -> None:
        check = re.findall(r"[0-9а-яА-Яa-zA-Z\s-]", value)
        if len(check) != len(value):
            raise ValidationError(f"The field {key} contains invalid characters")

    not_null_fields = ["settlement", "building", "house", "telephone", "street"]
    for key, value in data.items():
        if key in not_null_fields and value is None:
            raise ValidationError(f"The field {key} cannot be empty")

    need_list = ["settlement", "street", "house",
                 "structure", "building", "flat"]

    need_data = {key: value for key, value in data.items() if key in need_list}

    for key, value in need_data.items():
        check_by_regex(key, value)

    return data
