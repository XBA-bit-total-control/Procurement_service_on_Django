from .models import User
from random import choice


def get_random_admin() -> User:
    """Функция для получения случайного сотрудника.

    Returns:
        User: Случайный сотрудник.

    Raises:
        AssertionError: Если нет ни одного сотрудника.
    """
    try:
        admins = User.objects.filter(is_staff=True).all()
        return choice(admins)
    except IndexError:
        raise AssertionError("The project cannot work without at least one staff")


def get_random_activ_admin() -> User:
    """Функция для получения случайного активного сотрудника.

    Returns:
        User: Случайный активный сотрудник.

    Raises:
        AssertionError: Если нет ни одного сотрудника.
    """
    try:
        admins = User.objects.filter(is_staff=True, is_active=True).all()
        return choice(admins)
    except IndexError:
        return get_random_admin()


def get_random_superuser() -> User:
    """Функция для получения случайного администратора.

    Returns:
        User: Случайный администратор.

    Raises:
        AssertionError: Если нет ни одного администратора.
    """
    try:
        superusers = User.objects.filter(is_superuser=True).all()
        return choice(superusers)
    except IndexError:
        raise AssertionError("The project cannot work without at least one administrator")
