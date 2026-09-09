from .models import User
from random import choice


def get_random_admin():
    admins = User.objects.filter(is_staff=True).all()
    return choice(admins)


def get_random_activ_admin():
    try:
        admins = User.objects.filter(is_staff=True, is_active=True).all()
        return choice(admins)
    except IndexError:
        return get_random_admin()


def get_random_superuser():
    superusers = User.objects.filter(is_superuser=True).all()
    return choice(superusers)
