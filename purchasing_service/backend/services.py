from .models import User
from random import choice


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
