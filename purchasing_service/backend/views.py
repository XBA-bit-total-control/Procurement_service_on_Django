import json
import secrets

import requests
import yaml
from celery.result import AsyncResult
from django.core.validators import URLValidator, ValidationError
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from django_rest_passwordreset.serializers import EmailSerializer
from purchasing_service.settings import PARTNERSHIP_AGREEMENT
from requests.exceptions import ConnectionError, ConnectTimeout
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.filters import SearchFilter
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from yaml.parser import ParserError

from .data.body_of_letters import (completing_registration, order_created_for_user,
                                   order_created_for_admin, change_email_for_old,
                                   change_email_for_now, shop_registration)
from .filters import ShopFilter, CategoryFilter, ProductInfoFilter
from .models import (Category, ProductInfo, User, ConfirmationTokens,
                     Shop, Order, OrderItem, Contact)
from .serializers import (UserSerializer, ShopSerializer, ProductInfoSerializer,
                          PostProductInfoSerializer, OrderItemSerializer, PutOrderItemSerializer,
                          ContactSerializer, PutContactSerializer, OrderSerializer,
                          GetUserSerializer, PutUserSerializer, CategorySerializer,
                          PartnerOrderItemSerializer)
from .services import get_email_random_activ_admin, get_email_random_superuser
from .tasks import send_email, update_partner_price


@api_view(["POST"])
def user_register(request) -> Response:
    """Обработчик регистрации пользователя.

    Создаёт запись с неподтверждённым пользователем и отправляет письмо
    с токеном для завершения регистрации.
    """
    data = request.data

    serializer = UserSerializer(data=data)
    if not serializer.is_valid():
        return Response(
            {"error": serializer.errors},
            status=400
        )

    check_existing_user = User.objects.filter(email=serializer.validated_data["email"]).first()
    if check_existing_user:
        return Response(
            {"error": "User with this email already exists"},
            status=400
        )

    try:
        with transaction.atomic():
            user = User.objects.create_user(**serializer.validated_data)
            confirmation_token =  ConfirmationTokens.objects.create(
                user=user,
                token_for_email=secrets.token_urlsafe(12)
            )
    except IntegrityError:
        return Response(
            {
                "status": "fail",
                "error": "The request has been rejected due to a data conflict."
            },
            status=400
        )
    except Exception:
        return Response(
            {"error": f"Internal server error. "
                      f"If this happens again, please contact the administrator {get_email_random_superuser()}"},
            status=500
        )
    else:
        send_email.delay(
            subject="Registration on the Compraretis ad service",
            recipient=user.email,
            content=completing_registration(confirmation_token.token_for_email),
        )
        return Response(
            {
                "status": "success",
                "msg": "To complete registration, confirm your email"
            },
            status=201
        )


@api_view(["POST"])
def user_register_confirm(request) -> Response:
    """Обработчик завершения регистрации пользователя.

    Проверяет переданный токен и подтверждает профиль пользователя.
    """
    data = request.data

    email = data.get("email")
    if email is None:
        return Response(
            {"error": "You need to specify an email address"},
            status=400
        )
    check_email = EmailSerializer(data={"email": email})
    if not check_email.is_valid():
        return Response(
            {"error": "Invalid email address"},
            status=400
        )

    token = data.get("token")
    if token is None:
        return Response(
            {"error": "To confirm registration, you must provide a unique token"},
            status=400
        )
    if not isinstance(token, str):
        return Response(
            {"error": "Incorrect token format"},
            status=400
        )

    user = User.objects.filter(email=email).first()
    if user is None:
        return Response(
            {"error": f"The user with this email address [ {email} ] was not found. "
                      f"You should go through the registration procedure again"},
            status=404
        )
    if user.is_confirm:
        return Response(
            {"error": "The user has already been verified"},
            status=400
        )

    confirmation_token = ConfirmationTokens.objects.filter(user=user).first()
    if confirmation_token is None:
        return Response(
            {"error": "No confirmation token has been created for you. "
                      "Please register again."},
            status=400
        )
    else:
        if confirmation_token.token_for_email is None:
            return Response(
                {"error": "No confirmation token has been created for you. "
                          "Please register again."},
                status=400
            )

    if token != confirmation_token.token_for_email:
        return Response(
            {"error": "Invalid token"},
            status=400
        )

    user.is_confirm = True
    confirmation_token.token_for_email = None
    try:
        with transaction.atomic():
            user.save()
            confirmation_token.save()
    except IntegrityError:
        return Response(
            {
                "status": "fail",
                "error": "The request has been rejected due to a data conflict."
            },
            status=400
        )
    except Exception:
        return Response(
            {"error": f"Internal server error. "
                      f"If this happens again, please contact the administrator {get_email_random_superuser()}"},
            status=500
        )
    else:
        return Response(
            {
                "status": "success",
                "msg": "The user has been successfully verified"
            },
            status=201
        )


class UserDetailsAPIView(APIView):
    """Представление для получения и обновления данных пользователя."""

    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get(self, request) -> Response:
        serializer = GetUserSerializer(request.user)

        return Response(serializer.data)

    def put(self, request) -> Response:
        data = request.data
        serializer = PutUserSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.filter(id=request.user.id)
        email = serializer.validated_data.get("email")
        if email is not None:  # Предоставляется возможность смены email
            try:
                with transaction.atomic():
                    check_exist_email = User.objects.filter(email=email, is_confirm=True).first()
                    if check_exist_email is not None:
                        return Response(
                            {"error": "This email is already registered"},
                            status=400
                        )
                    else:
                        check_unconfirm_email = User.objects.filter(email=email, is_confirm=False).first()
                        if check_unconfirm_email is not None:
                            check_unconfirm_email.delete()

                    # Все существующие токены пользователя удаляются
                    tokens_for_delete = Token.objects.filter(user=request.user).all()
                    if tokens_for_delete:
                        for token in tokens_for_delete:
                            token.delete()

                    # Профиль пользователя назначается не подтвержденным
                    serializer.validated_data["is_confirm"] = False

                    user.update(**serializer.validated_data)

                    token_for_email = secrets.token_urlsafe(12)
                    confirmation_token, created = ConfirmationTokens.objects.get_or_create(
                        user=user.first(),
                        defaults={"token_for_email": token_for_email}
                    )
                    if not created:
                        confirmation_token.token_for_email = token_for_email
                        confirmation_token.save()

            except Exception:
                return Response(
                    {"error": f"Internal server error. "
                              f"If this happens again, please contact the administrator {get_email_random_superuser()}"},
                    status=500
                )
            else:
                # Уведомления пользователя по старому email и о его изменении
                send_email.delay(
                    subject="Compraretis service: change email",
                    recipient=request.user.email,
                    content=change_email_for_old(get_email_random_activ_admin()),
                )
                # Письмо для подтверждения профиля на новый email
                send_email.delay(
                    subject="Compraretis service: change email",
                    recipient=email,
                    content=change_email_for_now(token_for_email),
                )

                return Response(
                    {
                        "status": "success",
                        "msg": "Your email has been changed — please confirm it"
                    }
                )
        else:
            if len(serializer.validated_data) == 0:
                return Response(
                    {"error": "No correct data was provided for change"},
                    status=400
                )
            try:
                with transaction.atomic():
                    user.update(**serializer.validated_data)

                    # В ответе уточняются измененные поля для понимания пользователя
                    return Response(
                        {
                            "status": "success",
                            "msg": f"Changed: {', '.join([value for value in serializer.validated_data.keys()])}"
                        }
                    )
            except Exception:
                return Response(
                    {"error": f"Internal server error. "
                              f"If this happens again, please contact the administrator {get_email_random_superuser()}"},
                    status=500
                )


class ShopListView(GenericAPIView, ListModelMixin):
    """Представление для получения магазинов.

    Аутентификация не требуется.
    """
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = ShopFilter
    search_fields = ["name", "url"]
    queryset = Shop.objects.all()
    serializer_class = ShopSerializer
    pagination_class = PageNumberPagination
    pagination_class.page_size = 20

    def get(self, request):
        return self.list(request)


class CategoriesListView(GenericAPIView, ListModelMixin):
    """Представление для получения категорий.

    Аутентификация не требуется.
    """
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = CategoryFilter
    search_fields = ["name"]
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    pagination_class = PageNumberPagination

    def get(self, request):
        return self.list(request)


class ProductListView(GenericAPIView, ListModelMixin):
    """Представление для получения информации о товарах.

    Аутентификация не требуется.
    """
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = ProductInfoFilter
    search_fields = ["name"]
    queryset = ProductInfo.objects.all()
    serializer_class = ProductInfoSerializer
    pagination_class = PageNumberPagination

    def get(self, request):
        return self.list(request)


@api_view(["GET"])
def get_one_product(request, id) -> Response:
    """Обработчик для получения информации о товаре по идентификатору."""

    product = ProductInfo.objects.filter(id=id).first()
    if product is None:
        return Response(
            {"error": "Product not found"},
            status=404
        )
    serializer = ProductInfoSerializer(product)

    return Response(serializer.data)


class BasketAPIView(APIView):
    """Представление для работы с корзиной пользователя."""

    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get(self, request):
        """Получение содержимого корзины при его наличии.

        В ответе вместе с содержимым корзины предоставляется её общая стоимость.
        """
        order = Order.objects.filter(
            user=request.user,
            status="NOT_CREATED"
        ).first()
        if order is None:
            return Response(
                {"error": "Your cart has not yet been created"},
                status=404
            )

        content = OrderItem.objects.select_related("order").filter(
            order__user_id=request.user.id,
            order=order
        )
        if not content:
            return Response({"msg": "Your cart is empty"})
        serializer = OrderItemSerializer(content, many=True)

        data = list(serializer.data)
        cost_of_purchases = 0
        for content in serializer.data:
            cost_of_purchases += content["common_price"]

        data.append({"cost_of_purchases": cost_of_purchases})

        return Response(data)

    def post(self, request):
        """Добавление товара в корзину."""

        def add_order_item(
                product_info_id: int,
                quantity: int,
                order_id: int,
                order: Order
        ) -> bool:
            """Внутренняя функция для добавления товара в корзину.

            Args:
                product_info_id: идентификатор информации о товаре
                quantity: количество
                order_id: идентификатор заказа
                order: объект заказа

            Raises:
                AssertionError: когда товар не существует, уже есть в корзине
                    или запрашиваемое количество отсутствует в магазине.

            Returns:
                bool: True, если товар добавлен.
            """
            product_info = ProductInfo.objects.filter(id=product_info_id).first()
            if product_info is None:
                raise AssertionError(f"Product with id={product_info_id} not found")

            check_exist_order_item = OrderItem.objects.filter(
                product_info_id=product_info.id,
                order_id=order_id,
                shop_id=product_info.shop.id
            ).first()
            if check_exist_order_item:
                raise AssertionError("The product is already in your cart")

            if quantity > product_info.quantity:
                raise AssertionError(f"There are only {product_info.quantity} units of this product available -"
                                     f" you won't be able to order {quantity} units now")

            OrderItem.objects.create(
                order=order,
                product_info=product_info,
                shop=product_info.shop,
                quantity=quantity
            )
            return True

        try:
            data = request.data
            if isinstance(data, list):
                serializer = PostProductInfoSerializer(data=data, many=True)
            elif isinstance(data, dict):
                items = data.get("items")
                if isinstance(items, str):
                    py_items = json.loads(items)
                    serializer = PostProductInfoSerializer(data=py_items, many=True)
                else:
                    serializer = PostProductInfoSerializer(data=data)
            else:
                raise AssertionError("Invalid request body")

            serializer.is_valid(raise_exception=True)
            serializer_data = serializer.validated_data

            with transaction.atomic():
                order_ = Order.objects.filter(
                    user=request.user,
                    status="NOT_CREATED"
                ).first()
                if order_ is None:
                    order_ = Order.objects.create(user=request.user)

                if isinstance(serializer_data, list):
                    for item in serializer_data:
                        add_order_item(
                            product_info_id=item["product_info"],
                            quantity=item["quantity"],
                            order_id=order_.id,
                            order=order_
                        )
                    return Response(
                        {"status": "success"},
                        status=201
                    )

                product_info_id_ = serializer_data["product_info"]
                quantity_ = serializer_data["quantity"]
                add_order_item(
                    product_info_id=product_info_id_,
                    quantity=quantity_,
                    order_id=order_.id,
                    order=order_
                )
                return Response(
                    {"status": "success"},
                    status=201
                )

        except AssertionError as err:
            return Response(
                {
                    "status": "fail",
                    "error": err.__str__()
                },
                status=400
            )
        except IntegrityError:
            return Response(
                {
                    "status": "fail",
                    "error": "The request has been rejected due to a data conflict."
                },
                status=400
            )
        except json.decoder.JSONDecodeError:
            return Response(
                {"error": "An incorrect string value was passed "
                          "for decoding in the json format"},
                status=400
            )
        except Exception:
            return Response(
                {"error": f"Internal server error. "
                          f"If this happens again, please contact the administrator {get_email_random_superuser()}"},
                status=500
            )

    def put(self, request) -> Response:
        """Изменение количества товара в корзине."""

        def change_quantity(values_: dict) -> bool:
            """Внутренняя функция для изменения количества товара в корзине.

            Args:
                values_: словарь с данными

            Raises:
                AssertionError: если количество товара превышает имеющееся в наличии
                    или товара нет в корзине.

            Returns:
                bool: True при успешном выполнении.
            """
            serializer = PutOrderItemSerializer(data=values_)
            serializer.is_valid(raise_exception=True)
            serializer_data = serializer.validated_data

            id_ = serializer_data["id"]
            quantity = serializer_data["quantity"]
            order_item = OrderItem.objects.filter(
                id=id_,
                order__user_id=request.user.id
            ).first()

            if order_item is None:
                raise AssertionError(f"Your product with id={id_} is not in the cart")

            product_info = ProductInfo.objects.filter(id=order_item.product_info_id).first()
            if quantity > product_info.quantity:
                raise AssertionError(f"There are only {product_info.quantity} units of this product available -"
                                     f" you will not be able to add {quantity} units now")

            order_item.quantity = quantity
            order_item.save()
            return True

        try:
            with transaction.atomic():
                data = request.data
                if isinstance(data, list):
                    for values in data:
                        change_quantity(values)
                    return Response({"status": "success"})

                elif isinstance(data, dict):
                    items = data.get("items")
                    if items:
                        items = json.loads(items)
                        for values in items:
                            change_quantity(values)
                        return Response({"status": "success"})

                    change_quantity(data)
                    return Response({"status": "success"})

                else:
                    raise AssertionError("Invalid request body")

        except AssertionError as err:
            return Response(
                {
                    "status": "fail",
                    "error": err.__str__()
                },
                status=400
            )
        except IntegrityError:
            return Response(
                {
                    "status": "fail",
                    "error": "The request has been rejected due to a data conflict."
                },
                status=400
            )
        except json.decoder.JSONDecodeError:
            return Response(
                {"error": "An incorrect string value was passed "
                          "for decoding in the json format"},
                status=400
            )
        except Exception:
            return Response(
                {"error": f"Internal server error. "
                          f"If this happens again, please contact the administrator {get_email_random_superuser()}"},
                status=500
            )

    def delete(self, request) -> Response:
        """Удаление товаров из корзины."""

        data = request.data
        items = data.get("items")

        try:
            with transaction.atomic():
                if isinstance(items, int):
                    if items > 0:
                        list_id = [items]
                    else:
                        raise AssertionError("id must be greater than 0")

                elif isinstance(items, str):
                    if items == "":
                        raise AssertionError("The product ids in cart were not transmitted for deletion")
                    list_id = [int(num) for num in items.split(",")]

                elif isinstance(items, list):
                    for item in items:
                        if not isinstance(item, int):
                            raise AssertionError(f"Invalid value for the id -> {item}")
                    list_id = items

                elif items is None:
                    raise AssertionError("items is required")

                else:
                    raise AssertionError("items must be a string or a list")

                for order_item_id in list_id:
                    order_item = OrderItem.objects.filter(
                        id=order_item_id,
                        order__user_id=request.user.id
                    ).first()

                    if order_item is None:
                        raise AssertionError(f"The product with id={order_item_id}"
                                             f" is not in the list for deletion")
                    order_item.delete()

                return Response({"status": "success"})

        except AssertionError as err:
            return Response(
                {
                    "status": "fail",
                    "error": err.__str__()
                },
                status=400
            )
        except IntegrityError:
            return Response(
                {
                    "status": "fail",
                    "error": "The request has been rejected due to a data conflict."
                },
                status=400
            )
        except ValueError:
            return Response(
                {
                    "status": "fail",
                    "error": "Invalid value for the id"
                },
                status=400
            )
        except Exception:
            return Response(
                {"error": f"Internal server error. "
                          f"If this happens again, please contact the administrator {get_email_random_superuser()}"},
                status=500
            )


class ContactAPIView(APIView):
    """Преставление для работы с контактами пользователя."""

    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get(self, request) -> Response:
        """Получение списка контактов пользователя, при наличии."""

        contacts = Contact.objects.filter(user=request.user).all()
        if not bool(contacts):
            return Response({"msg": "You haven’t provided your contact information yet"})
        serializer = ContactSerializer(contacts, many=True)

        return Response(serializer.data)

    def post(self, request) -> Response:
        """Создание нового контакта.

        Ограничение на количество контактов - 5.
        """
        serializer = ContactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        contacts = Contact.objects.filter(user=request.user).all()
        if len(contacts) == 5:
            return Response(
                {"error": "You have already created 5 contacts. "
                          "Please use them and, if necessary, delete or modify them"},
                status=400
            )
        serializer.validated_data["user_id"] = request.user.id
        serializer.validated_data.pop("id", None)
        Contact.objects.create(**serializer.validated_data)

        return Response(
            {"status": "success"},
            status=201
        )

    def put(self, request) -> Response:
        """Изменение контакта."""

        data = request.data
        if not data:
            return Response(
                {"error": "request body is empty"},
                status=400
            )

        # Проверка на null значения для недопустимых полей
        not_null_fields = ["settlement", "building", "house", "telephone"]
        for key, value in data.items():
            if key in not_null_fields and value is None:
                return Response(
                    {"error": f"The field {key} cannot be empty"},
                    status=400
                )

        serializer = PutContactSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        id_ = serializer.validated_data.pop("id")
        contacts = Contact.objects.filter(id=id_, user=request.user)
        if not bool(contacts):
            return Response(
            {"error": f"There’s nothing to change. "
                      f"The contact data belonging to you with id={id_} is missing"},
            status=404
        )
        contacts.update(**serializer.validated_data)

        return Response({"status": "success"})

    def delete(self, request) -> HttpResponse | Response:
        """Удаление контакта."""

        data = request.data
        items = data.get("items")

        try:
            with transaction.atomic():
                if items is None:
                    raise AssertionError("items is required")

                elif isinstance(items, int):
                    if items > 0:
                        list_id = [items]
                    else:
                        raise AssertionError("id must be greater than 0")

                elif isinstance(items, str):
                    if items == "":
                        raise AssertionError("The product ids in cart were not transmitted for deletion")
                    list_id = [int(num) for num in items.split(",")]

                elif isinstance(items, list):
                    for item in items:
                        if not isinstance(item, int):
                            raise AssertionError(f"Invalid value for the id -> {item}")
                    list_id = items

                else:
                    raise AssertionError("items must be a string or a list")

                for contact_id in list_id:
                    contact = Contact.objects.filter(
                        id=contact_id,
                        user=request.user
                    ).first()

                    if contact is None:
                        raise AssertionError(f"No contact to delete. "
                      f"The contact data belonging to you with id={contact_id} is missing")
                    contact.delete()

                return HttpResponse(status=204)

        except AssertionError as err:
            return Response(
                {
                    "status": "fail",
                    "error": err.__str__()
                },
                status=400
            )
        except IntegrityError:
            return Response(
                {
                    "status": "fail",
                    "error": "The request has been rejected due to a data conflict."
                },
                status=400
            )
        except ValueError:
            return Response(
                {
                    "status": "fail",
                    "error": "Invalid value for the id"
                },
                status=400
            )
        except Exception:
            return Response(
                {"error": f"Internal server error. "
                          f"If this happens again, please contact the administrator {get_email_random_superuser()}"},
                status=500
            )


class OrderAPIView(APIView):
    """Представление для работы с заказами."""

    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get(self, request):
        """Получение списка заказов."""

        orders = Order.objects.filter(user=request.user).exclude(status="NOT_CREATED").all()
        serializer = OrderSerializer(orders, many=True)

        return Response(serializer.data)

    def post(self, request):
        """Создание заказа."""

        data = request.data
        try:
            with transaction.atomic():
                contact_id = data.get("contact")

                if contact_id is None:
                    return Response(
                        {"error": "contact is required"},
                        status=400
                    )
                elif isinstance(contact_id, int):
                    pass
                elif isinstance(contact_id, str):
                    contact_id = int(contact_id)
                else:
                    return Response(
                        {"error": "Invalid value for the contact"},
                        status=400
                    )

                if contact_id < 1:
                    return Response(
                        {"error": "contact must be greater than 0"},
                        status=400
                    )

                order = Order.objects.filter(
                    user=request.user,
                    status="NOT_CREATED"
                ).first()
                if order is None:
                    return Response(
                        {"error": "Your cart has not yet been created"},
                        status=404
                    )

                contact = Contact.objects.filter(user=request.user, id=contact_id).first()
                if contact is None:
                    return Response(
                        {"error": f"The contact data belonging to you with id={contact_id} is missing"},
                        status=404
                    )

                # Проверка на наличие товаров в корзине
                cart_contents = OrderItem.objects.select_related("order").filter(
                    order__user_id=request.user.id,
                    order__status="NOT_CREATED"
                )
                if not cart_contents:
                    return Response(
                        {"error": "Your cart is empty — you won’t be able to place an order"},
                        status=400
                    )

                # Проверка на наличие нужного количеств товара в магазине
                for goods in cart_contents.all():
                    product_info = ProductInfo.objects.filter(id=goods.product_info_id).first()
                    if product_info.quantity < goods.quantity:
                        return Response(
                            {"error": f"There are only {product_info.quantity} units of this product available -"
                                      f" you won't be able to order {goods.quantity} units now"}
                        )

                serializer = OrderItemSerializer(cart_contents, many=True)

                order.status = "PROCESSING"
                order.created_at = timezone.now()
                order.contact = contact
                order.save()

                # Формирование общей цены заказа
                price = 0
                for cart_contents in serializer.data:
                    price += cart_contents["common_price"]

                content_for_user = order_created_for_user(
                    order_id=order.id,
                    order_price=price,
                    username=request.user.first_name
                )
                content_for_admin = order_created_for_admin(
                    order_id=order.id,
                    order_price=price,
                    username=request.user.first_name,
                    user_id=request.user.id
                )

        except ValueError:
            return Response(
                {"error": "Invalid value for the contact"},
                status=400
            )
        except Exception:
            return Response(
                {"error": f"Internal server error. "
                          f"If this happens again, please contact the administrator {get_email_random_superuser()}"},
                status=500
            )
        else:
            # Отправка письма пользователю о принятии заказа в обработку
            send_email.delay(
                subject="Compraretis service: Order confirmation",
                recipient=request.user.email,
                content=content_for_user
            )
            # Отправка письма сотруднику на проверку и подтверждение
            admin_email = get_email_random_activ_admin()
            if admin_email != "":
                send_email.delay(
                    subject="Compraretis service: New order",
                    recipient=admin_email,
                    content=content_for_admin
                )

            return Response(
                {"status": "success"},
                status=201
            )


@api_view(["POST"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def register_partner(request) -> Response:
    """Обработчик для регистрации партнера.

    Создает запись о магазине с принадлежностью к пользователю
    и отправляет письмо с токеном и партнерским соглашением на почту
    для завершения регистрации партнера.
    """
    data = request.data

    if request.user.is_shop:
        return Response(
            {"error": "You are already our partner"},
            status=403
        )
    if not request.user.is_active:
        return Response(
            {"error": "Inactive users cannot become partners"},
            status=403
        )
    if not request.user.is_confirm:
        return Response(
            {"error": "Your profile is not verified. Complete the registration"},
            status=400
        )

    if isinstance(data, dict):
        items = data.get("items")
        if isinstance(items, str):
            py_items = json.loads(items)
            if isinstance(py_items, list):
                if len(py_items) > 1:
                    return Response(
                        {"error": "There are too many values in the request body"},
                        status=400
                    )
                if not isinstance(py_items[0], dict):
                    return Response(
                        {"error": "Invalid request body"},
                        status=400
                    )
                serializer = ShopSerializer(data=py_items[0])
            elif isinstance(py_items, dict):
                serializer = ShopSerializer(data=py_items)
            else:
                return Response(
                {"error": "Invalid request body"},
                    status=400
                )
        else:
            serializer = ShopSerializer(data=data)
    else:
        return Response(
            {"error": "Invalid request body"},
            status=400
        )
    serializer.is_valid(raise_exception=True)

    if Shop.objects.filter(name=serializer.validated_data["name"]).exists():
        return Response(
            {"error": "A shop with that name already exists"},
            status=400
        )
    if serializer.validated_data["url"] is not None:
        if Shop.objects.filter(url=serializer.validated_data["url"]).exists():
            return Response(
                {"error": "A shop with that url already exists"},
                status=400
            )
    serializer.validated_data.pop("id", None)

    try:
        with transaction.atomic():
            Shop.objects.create(
                **serializer.validated_data,
                user=request.user
            )

            token_for_partner = secrets.token_urlsafe(12)
            confirmation_token, created = ConfirmationTokens.objects.get_or_create(
                user=request.user,
                defaults={"token_for_partner": token_for_partner}
            )
            if not created:
                confirmation_token.token_for_partner = token_for_partner
                confirmation_token.save()

            body_email = shop_registration(
                first_name=request.user.first_name,
                token=token_for_partner,
                link_to_agreement=PARTNERSHIP_AGREEMENT
            )

    except json.decoder.JSONDecodeError:
        return Response(
            {"error": "An incorrect string value was passed "
                      "for decoding in the json format"},
            status=400
        )
    except IntegrityError:
        return Response(
            {
                "status": "fail",
                "error": "The request has been rejected due to a data conflict."
            },
            status=400
        )
    except Exception:
        return Response(
            {"error": f"Internal server error. "
                      f"If this happens again, please contact the administrator {get_email_random_superuser()}"},
            status=500
        )
    else:
        send_email.delay(
            subject="Compraretis service: The beginning of the partnership",
            recipient=request.user.email,
            content=body_email
        )

        return Response(
            {
                "status": "success",
                "msg": "To complete the partnership agreement, please check you the email address"
            },
            status=201
        )


@api_view(["POST"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def register_partner_confirm(request) -> Response:
    """Обработчик завершения регистрации партнера.

    Проверяет переданный токен и устанавливает флаг is_shop для пользователя в True.
    """
    data = request.data

    if request.user.is_shop:
        return Response(
            {"error": "You are already our partner"},
            status=403
        )
    if not request.user.is_active:
        return Response(
            {"error": "Inactive users cannot become partners"},
            status=403
        )
    if not request.user.is_confirm:
        return Response(
            {"error": "Your profile is not verified. Complete the registration"},
            status=400
        )

    token = data.get("token")
    if token is None:
        return Response(
            {"error": "To confirm registration, you must provide a unique token"},
            status=400
        )
    if not isinstance(token, str):
        return Response(
            {"error": "Incorrect token format"},
            status=400
        )

    confirmation_token = ConfirmationTokens.objects.filter(user=request.user).first()
    if confirmation_token is None:
        return Response(
            {"error": f"No confirmation token has been created for you. "
                      "Please go through the partner registration procedure again"},
            status=400
        )
    else:
        if confirmation_token.token_for_partner is None:
            return Response(
                {"error": f"No confirmation token has been created for you. "
                          "Please go through the partner registration procedure again"},
                status=400
            )

    if token != confirmation_token.token_for_partner:
        return Response(
            {"error": "Invalid token"},
            status=400
        )

    try:
        with transaction.atomic():
            request.user.is_shop = True
            request.user.save()

            confirmation_token.token_for_partner = None
            confirmation_token.save()

            return Response(
                {
                    "status": "success",
                    "msg": "You have become our partner"
                },
                status=201
            )

    except IntegrityError:
        return Response(
            {
                "status": "fail",
                "error": "The request has been rejected due to a data conflict."
            },
            status=400
        )
    except Exception:
        return Response(
            {"error": f"Internal server error. "
                      f"If this happens again, please contact the administrator {get_email_random_superuser()}"},
            status=500
        )


class PartnerStateAPIView(APIView):
    """Представление для статуса партнера."""

    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get(self, request, internal=False) -> Response | Shop:
        """Получение статуса партнера.

        Поддерживает использование в других методах представления.

        Args:
            internal: флаг для получения объекта магазина

        Returns:
            Response: ответ со статусом партнера
            Shop: объект магазина
        """
        if not request.user.is_shop:
            return Response(
                {"error": "You are not our partner"},
                status=403
            )
        shop = Shop.objects.filter(user=request.user).first()
        if shop is None:
            return Response(
                {"error": "There is no information about the partnership. "
                          "Please, register the shop"},
                status=404
            )
        if internal:
            return shop
        else:
            return Response(
                {
                    "status": "success",
                    "partner_status": f"{shop.status}"
                }
            )

    def patch(self, request) -> Response:
        """Изменение статуса партнера."""

        data = request.data
        status = data.get("status")
        shop = PartnerStateAPIView.get(self, request, internal=True)

        if isinstance(shop, Response):
            return shop

        if status is None:
            return Response(
                {"error": "status is required"},
                status=400
            )
        if not isinstance(status, str):
            return Response(
                {"error": "The status value is a string"},
                status=400
            )
        if status in ["принимаю", "ACCEPT_ORDERS"]:
            shop.status = "ACCEPT_ORDERS"
        elif status in ["не принимаю", "NOT_ACCEPT_ORDERS"]:
            shop.status = "NOT_ACCEPT_ORDERS"
        else:
            return Response(
                {"error": "Incorrect value for the status. "
                          "Available only ‘принимаю’ and ‘не принимаю’"},
                status=400
            )
        shop.save()

        return Response(
            {"status": "success"}
        )


class PartnerOrdersAPIView(APIView):
    """Представление для получения заказов партнером."""

    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get(self, request) -> Response:
        """Получение заказов партнера.

        Возвращает подробную информацию о заказах.
        """
        shop = PartnerStateAPIView.get(self, request, internal=True)
        if isinstance(shop, Response):
            return shop

        order_items = (OrderItem.objects
                       .filter(shop=shop)
                       .exclude(order__status="NOT_CREATED")  # Исключаются заказы являющиеся корзиной пользователя
                       .order_by('-order__status')
                       .all())

        if not bool(order_items):
            return Response(
                {"msg": "No orders"}
            )

        serializer = PartnerOrderItemSerializer(order_items, many=True)

        return Response(serializer.data)


@api_view(["POST"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def data_import(request) -> Response:
    """Обработчик обновления прайса партнера."""

    # Проверка является ли пользователь магазином/партнером
    if not request.user.is_shop:
        return Response(
            {"error": "You are not our partner"},
            status=403
        )

    data = request.data
    url = data.get("url")
    if not url:
        return Response(
            {"error": "Url was not sent"},
            status=400
        )

    # Проверка валидности url
    check_url = URLValidator()
    try:
        check_url(url)
    except ValidationError:
        return Response(
            {"error": "An invalid url was sent"},
            status=400
        )

    # Попытка получить данные из url
    try:
        for _ in range(3):
            response = requests.get(url)
            if response.status_code == 200:
                break
        else:
            return Response(
                {"error": "No data was received from the transmitted url"},
                status=400
            )
    except ConnectTimeout:
        return Response(
            {"error": "It was not possible to contact the server using "
                      "the transmitted url - no response was received from it"},
            status=400
        )
    except ConnectionError:
        return Response(
            {"error": "It is not possible to establish a connection "
                      "to receive data at the specified url"},
            status=400
        )

    # Извлечение данных
    yaml_data = response.content
    try:
        dict_data = yaml.safe_load(yaml_data)
    except ParserError:
        return Response(
            {"error": "Invalid data format in a YAML file"},
            status=400
        )

    user_id = request.user.id
    # Проверка по объёму данных на необходимость передачи задачи в Celery
    if len(dict_data.get("goods", [])) > 100:
        task_celery = update_partner_price.delay(user_id, dict_data, for_celery=True)
        return Response(
            {
                "status": "success",
                "msg": f"The data has been accepted for processing - you can get the result"
                       f" from the resource api/v1/partner/data_import/result/{task_celery.id}"
            },
            status=201
        )
    else:
        return update_partner_price(user_id, dict_data)


@api_view(["GET"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def data_import_result(request, task_id: str) -> Response:
    """Обработчик получения результата обновления прайса партнера.

    Для тех случаев, когда обработка данных была передана Celery.
    """
    task_celery = AsyncResult(task_id)
    if task_celery.status == "SUCCESS":
        return Response(task_celery.result)
    elif task_celery.status == "FAILURE":
        return Response(
            {"error": f"Internal server error. "
                      f"If this happens again, please contact the administrator {get_email_random_superuser()}"},
            status=500
        )
    else:
        return Response(
            {"msg": f"Processing data in the {task_celery.status} status"}
        )
