import json
import secrets

import requests
import yaml
from django.core.validators import URLValidator, ValidationError
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from django_rest_passwordreset.serializers import EmailSerializer
from requests.exceptions import ConnectionError, ConnectTimeout
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view
from rest_framework.filters import SearchFilter
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .data.body_of_letters import (completing_registration, order_created_for_user,
                                   order_created_for_admin, change_email_for_old,
                                   change_email_for_now)
from .email_mailing import send_email
from .filters import UserFilter, ShopFilter, CategoryFilter
from .models import (Category, ProductInfo, Parameter, User,
                     ProductParameter, Shop, ShopCategory, Product,
                     Order, OrderItem, Contact)
from .serializers import (UserSerializer, ShopSerializer, ProductInfoSerializer,
                          PostProductInfoSerializer, OrderItemSerializer, PutOrderItemSerializer,
                          ContactSerializer, PutContactSerializer, OrderSerializer,
                          GetUserSerializer, PutUserSerializer, CategorySerializer)
from .services import get_random_activ_admin, get_random_superuser


@api_view(["POST"])
def data_import(request) -> Response:
    """
    A view for importing data from the url
    of the format referring to the file.yaml

    :returns: Response with json content
    """
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

    # Попытка получить данные
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
    dict_data = yaml.safe_load(yaml_data)

    # Подготовка ответа в виде небольшого отчета
    response_report = Response(data={"status": "success"})
    response_report.status_code = 201

    categories = dict_data.get("categories")
    goods = dict_data.get("goods")
    shop = dict_data.get("shop")
    if shop is None:
        return Response(
            {"error": "Data import error. The required 'shop' field was not specified"},
            status=400
        )
    shop_obj = Shop.objects.filter(name=shop).first()
    if not shop_obj:
        return Response(
            {"error": f"Data import error. The specified store '{shop}' does not exist. "
                      f"Create a store or change its name"},
            status=400
        )
    if categories is None and goods is None:
        return Response(
            {"error": "Data import error. There is no record data in the provided URL information"},
            status=400
        )
    try:
        with transaction.atomic():
            # Блок проверки и записи категорий
            if categories:
                response_report.data["categories"] = 0
                for category in categories:
                    id = category.get("id")
                    name = category.get("name")
                    if not name:
                        raise IntegrityError("The required category name was not "
                                             "specified in the file submitted for data import")

                    if id:
                        category_obj = Category.objects.filter(id=id).first()
                        if category_obj:
                            if category_obj.name != name:
                                return Response(
                                    {"error": f"This id={id} is already in use for the category - select another"},
                                    status=400
                                )
                        else:
                            category_obj = Category.objects.create(
                                id=id,
                                name=name,
                            )
                            created = True
                    else:
                        category_obj, created = Category.objects.get_or_create(
                            name=name,
                            defaults={"name": name}
                        )
                    if created:
                        ShopCategory.objects.create(
                            shop=shop_obj,
                            category=category_obj
                        )
                        response_report.data["categories"] += 1  # Внесение отчетности

                # Фиксация внесенных изменений
                if response_report.data["categories"] > 0:
                    response_report.data["categories"] = f"uploaded {response_report.data["categories"]} records"
                else:
                    response_report.data.pop("categories")

            # Блок проверки и записи товаров
            if goods:
                response_report.data["product_information"] = 0  # Добавление блока для ответа
                for good in goods:
                    category = good.get("category")
                    if not category:
                        raise IntegrityError("Product was not assigned a category attribute")
                    else:
                        if not isinstance(category, int):
                            raise IntegrityError("The category attribute must be a string")

                    id = good.get("id")
                    if id:
                        if not isinstance(id, int):
                            raise IntegrityError("The id attribute must be a string")
                        # Проверка на наличие информации о товаре
                        check_obj_by_id = ProductInfo.objects.filter(id=id).first()
                        if check_obj_by_id:
                            raise IntegrityError(f"The product info with id={id} already exists")

                    model = good.get("model")
                    if not model:
                        raise IntegrityError("Product was not assigned a model attribute")
                    else:
                        if not isinstance(model, str):
                            raise IntegrityError("The model attribute must be a string")

                    name = good.get("name")
                    if not name:
                        raise IntegrityError("Product was not assigned a name attribute")
                    else:
                        if not isinstance(name, str):
                            raise IntegrityError("The name attribute must be a string")

                    parameters = good.get("parameters")
                    if parameters:
                        if not isinstance(parameters, dict):
                            raise IntegrityError("The parameters attribute must be a dictionary")
                        for parameter, value in parameters.items():
                            if not isinstance(parameter, str):
                                raise IntegrityError("Parameter name/key must be a string")
                            if not isinstance(value, str | int | float | bool):
                                raise IntegrityError("Parameter value must be a string, number, or boolean")

                    price = good.get("price")
                    if not price:
                        raise IntegrityError("Product was not assigned a price attribute")
                    else:
                        if not isinstance(price, int | float):
                            raise IntegrityError("The price attribute must be a number")
                        if price < 0:
                            raise IntegrityError("The price attribute must be a positive number")

                    price_rrc = good.get("price_rrc")
                    if price_rrc:
                        if not isinstance(price_rrc, int | float):
                            raise IntegrityError("The price_rrc attribute must be a number")
                        if price_rrc < 0:
                            raise IntegrityError("The price_rrc attribute must be a positive number")

                    quantity = good.get("quantity")
                    if not quantity:
                        raise IntegrityError("Product was not assigned a quantity attribute")
                    else:
                        if not isinstance(quantity, int):
                            raise IntegrityError("The quantity attribute must be a number")
                        if quantity <= 0:
                            raise IntegrityError("The quantity attribute must be a positive number")

                    category_obj = Category.objects.filter(id=category).first()
                    if not category_obj:
                        raise IntegrityError(f"Category with id={category} does not exist")

                    product = Product.objects.filter(
                        name=name,
                        category=category_obj
                    )
                    if not product:
                        product = Product(
                            name=name,
                            category=category_obj
                        )
                        product.save()

                    if id:
                        product_info = ProductInfo(
                            id=id,
                            product=product,
                            shop=shop_obj,
                            model=model,
                            name=name,
                            price=price,
                            price_rrc=price_rrc,
                            quantity=quantity
                        )
                        product_info.save()
                    else:
                        product_info = ProductInfo(
                            product=product,
                            shop=shop_obj,
                            model=model,
                            name=name,
                            price=price,
                            price_rrc=price_rrc,
                            quantity=quantity
                        )
                        product_info.save()

                    for parameter, value in parameters.items():
                        if isinstance(value, bool):
                            value = str(value)
                        parameter, _ = Parameter.objects.get_or_create(
                            name=parameter,
                            defaults={"name": parameter}
                        )
                        ProductParameter(
                            product_info=product_info,
                            parameter=parameter,
                            value=value
                        ).save()
                    response_report.data["product_information"] += 1  # Внесение отчетности

            # Формирование ответа
            response_report.data[
                "product_information"] = f"uploaded {response_report.data['product_information']} records"

            return response_report

    except IntegrityError as err:
        return Response(
            {"error": f"Data import error. {err.__str__()}"},
            status=400
        )
    except Exception as err:
        return Response(
            {"error": f"{err.__class__.__name__} + {err.__str__()}"},
            status=500
        )


@api_view(["POST"])
def user_register(request) -> Response:
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
    serializer.validated_data["registration_token"] = secrets.token_urlsafe(12)

    try:
        with transaction.atomic():
            user = User.objects.create_user(**serializer.validated_data)
            send_email(
                subject="Registration on the Compraretis ad service",
                recipient=user.email,
                content=completing_registration(user.registration_token),
            )
    except IntegrityError as err:
        return Response(
            {
                "status": "fail",
                "error": f"{err.__str__()}"
            },
            status=400
        )
    except Exception as err:
        return Response(
            {
                "status": "fail",
                "error": f"{err.__class__.__name__} + {err.__str__()}"
            },
            status=500
        )
    else:
        return Response(
            {
                "status": "success",
                "msg": "To complete registration, confirm your email"
            },
            status=201
        )


@api_view(["POST"])
def user_register_confirm(request) -> Response:
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

    if token != user.registration_token:
        return Response(
            {"error": "Invalid token"},
            status=400
        )

    user.is_confirm = True
    user.registration_token = None
    try:
        with transaction.atomic():
            user.save()
    except IntegrityError as err:
        return Response(
            {
                "status": "fail",
                "error": f"{err.__str__()}"
            },
            status=400
        )
    except Exception as err:
        return Response(
            {
                "status": "fail",
                "error": f"{err.__class__.__name__} + {err.__str__()}"
            },
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


class UserDetailsListView(GenericAPIView, ListModelMixin):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = UserFilter
    serializer_class = GetUserSerializer
    search_fields = ["first_name", "last_name", "patronymic"]
    queryset = User.objects.exclude(
        is_superuser=True).exclude(
        is_staff=True).exclude(
        is_shop=True).all()

    def get(self, request):
        return self.list(request)

    def put(self, request):
        data = request.data
        serializer = PutUserSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                user = User.objects.filter(id=request.user.id)
                email = serializer.validated_data.get("email")
                if email is not None:
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

                    tokens_for_delete = Token.objects.filter(user=request.user).all()
                    if tokens_for_delete:
                        for token in tokens_for_delete:
                            token.delete()

                    registration_token = secrets.token_urlsafe(12)

                    serializer.validated_data["is_confirm"] = False
                    serializer.validated_data["registration_token"] = registration_token

                    send_email(
                        subject="Compraretis service: change email",
                        recipient=request.user.email,
                        content=change_email_for_old(get_random_activ_admin().email),
                    )

                    user.update(**serializer.validated_data)

                    send_email(
                        subject="Compraretis service: change email",
                        recipient=email,
                        content=change_email_for_now(registration_token),
                    )

                    return Response(
                        {
                            "status": "success",
                            "msg": "Your email has been changed — please confirm it"
                        }
                    )
                user.update(**serializer.validated_data)

                return Response(
                    {"status": "success"}
                )

        except Exception:
            return Response(
                {"error": f"Internal server error. "
                          f"If this happens again, please contact the administrator {get_random_superuser().email}"},
                status=500
            )


class ShopListView(GenericAPIView, ListModelMixin):
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = ShopFilter
    search_fields = ["name", "url"]
    queryset = Shop.objects.all()
    serializer_class = ShopSerializer
    pagination_class = PageNumberPagination
    pagination_class.page_size = 12

    def get(self, request):
        return self.list(request)


class CategoriesListView(GenericAPIView, ListModelMixin):
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = CategoryFilter
    search_fields = ["name"]
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    pagination_class = PageNumberPagination
    pagination_class.page_size = 20

    def get(self, request):
        return self.list(request)


@api_view(["GET"])
def get_products(request) -> Response:
    shop_id = request.GET.get("shop_id")
    category_id = request.GET.get("category_id")
    if shop_id and category_id:
        products = ProductInfo.objects.select_related("product__category", "shop").filter(
            shop_id=shop_id,
            product__category_id=category_id
        )
    elif shop_id:
        products = ProductInfo.objects.select_related("shop").filter(shop_id=shop_id)
    elif category_id:
        products = ProductInfo.objects.select_related("product__category").filter(
            product__category_id=category_id
        )
    else:
        products = ProductInfo.objects.all()
    if not products:
        return Response(
            {"msg": "There is no products satisfying the request parameters"},
            status=404
        )

    paginator = PageNumberPagination()
    paginator.page_size = 30

    pages = paginator.paginate_queryset(products, request)
    serializer = ProductInfoSerializer(pages, many=True)

    return paginator.get_paginated_response(serializer.data)


class BasketAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get(self, request):
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
        def add_order_item(
                product_info_id: int,
                quantity: int,
                order_id: int
        ) -> bool:
            product_info = ProductInfo.objects.filter(id=product_info_id).first()
            if product_info is None:
                raise IntegrityError(f"Product with id={product_info_id} not found")

            check_exist_order_item = OrderItem.objects.filter(
                product_info_id=product_info.product.id,
                order_id=order_id,
                shop_id=product_info.shop.id
            ).first()
            if check_exist_order_item:
                raise IntegrityError("The product is already in your cart")

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
                raise IntegrityError("Invalid request body")

            serializer.is_valid(raise_exception=True)
            serializer_data = serializer.validated_data

            with transaction.atomic():
                order = Order.objects.filter(
                    user=request.user,
                    status="NOT_CREATED"
                ).first()
                if order is None:
                    order = Order.objects.create(user=request.user)

                if isinstance(serializer_data, list):
                    for item in serializer_data:
                        add_order_item(
                            item["product_info"],
                            item["quantity"],
                            order.id
                        )
                    return Response(
                        {"status": "success"},
                        status=201
                    )

                product_info_id_ = serializer_data["product_info"]
                quantity_ = serializer_data["quantity"]
                add_order_item(product_info_id_, quantity_, order.id)
                return Response(
                    {"status": "success"},
                    status=201
                )

        except IntegrityError as err:
            return Response(
                {
                    "status": "fail",
                    "error": err.__str__()
                },
                status=400
            )
        except json.decoder.JSONDecodeError:
            return Response(
                {"error": "An incorrect string value was passed "
                          "for decoding in the json format"},
                status=400
            )
        except Exception as err:
            return Response(
                {
                    "status": "fail",
                    "error": f"{err.__class__.__name__} + {err.__str__()}"
                },
                status=500
            )

    def put(self, request) -> Response:
        def change_quantity(values_: dict) -> bool:
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
                raise IntegrityError(f"Your product with id={id_} is not in the cart")

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
                    raise IntegrityError("Invalid request body")

        except IntegrityError as err:
            return Response(
                {
                    "status": "fail",
                    "error": err.__str__()
                },
                status=400
            )
        except json.decoder.JSONDecodeError:
            return Response(
                {"error": "An incorrect string value was passed "
                          "for decoding in the json format"},
                status=400
            )
        except Exception as err:
            return Response(
                {
                    "status": "fail",
                    "error": f"{err.__class__.__name__} + {err.__str__()}"
                },
                status=500
            )

    def delete(self, request) -> Response:
        data = request.data
        items = data.get("items")

        try:
            with transaction.atomic():
                if isinstance(items, str):
                    if items == "":
                        raise IntegrityError("The product ids in cart were not transmitted for deletion")
                    list_id = [int(num) for num in items.split(",")]

                elif isinstance(items, list):
                    for item in items:
                        if not isinstance(item, int):
                            raise IntegrityError(f"Invalid value for the id -> {item}")
                    list_id = items

                elif items is None:
                    raise IntegrityError("items is required")

                else:
                    raise IntegrityError("items must be a string or a list")

                for order_item_id in list_id:
                    order_item = OrderItem.objects.filter(
                        id=order_item_id,
                        order__user_id=request.user.id
                    ).first()

                    if order_item is None:
                        raise IntegrityError(f"The product with id={order_item_id}"
                                             f" is not in the list for deletion")
                    order_item.delete()

                return Response({"status": "success"})

        except IntegrityError as err:
            return Response(
                {
                    "status": "fail",
                    "error": err.__str__()
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
        except Exception as err:
            return Response(
                {
                    "status": "fail",
                    "error": f"{err.__class__.__name__} + {err.__str__()}"
                },
                status=500
            )


class ContactAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get(self, request) -> Response:
        contacts = Contact.objects.filter(user=request.user)
        if not contacts:
            return Response({"msg": "You haven’t provided your contact information yet."})
        serializer = OrderItemSerializer(data=contacts)

        return Response(serializer.data)

    def post(self, request) -> Response:
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
        Contact.objects.create(**serializer.validated_data)

        return Response(
            {"status": "success"},
            status=201
        )

    def put(self, request) -> Response:
        data = request.data
        if not data:
            return Response(
                {"error": "request body is empty"},
                status=400
            )

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
        data = request.data
        items = data.get("items")

        try:
            with transaction.atomic():
                if items is None:
                    raise IntegrityError("items is required")

                elif isinstance(items, int):
                    if items > 0:
                        list_id = [items]
                    else:
                        raise IntegrityError("id must be greater than 0")

                elif isinstance(items, str):
                    if items == "":
                        raise IntegrityError("The product ids in cart were not transmitted for deletion")
                    list_id = [int(num) for num in items.split(",")]

                elif isinstance(items, list):
                    for item in items:
                        if not isinstance(item, int):
                            raise IntegrityError(f"Invalid value for the id -> {item}")
                    list_id = items

                else:
                    raise IntegrityError("items must be a string or a list")

                for contact_id in list_id:
                    contact = Contact.objects.filter(
                        id=contact_id,
                        user=request.user
                    ).first()

                    if contact is None:
                        raise IntegrityError(f"No contact to delete. "
                      f"The contact data belonging to you with id={contact_id} is missing")
                    contact.delete()

                return HttpResponse(status=204)

        except IntegrityError as err:
            return Response(
                {
                    "status": "fail",
                    "error": err.__str__()
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
        except Exception as err:
            return Response(
                {
                    "status": "fail",
                    "error": f"{err.__class__.__name__} + {err.__str__()}"
                },
                status=500
            )


class OrderAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get(self, request):
        orders = Order.objects.filter(user=request.user).exclude(status="NOT_CREATED").all()
        serializer = OrderSerializer(orders, many=True)

        return Response(serializer.data)

    def post(self, request):
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

                cart_contents = OrderItem.objects.select_related("order").filter(
                    order__user_id=request.user.id,
                    order__status="NOT_CREATED"
                )
                if not cart_contents:
                    return Response(
                        {"error": "Your cart is empty — you won’t be able to place an order"},
                        status=400
                    )
                serializer = OrderItemSerializer(cart_contents, many=True)

                order.status = "PROCESSING"
                order.created_at = timezone.now()
                order.save()

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

                send_email(
                    subject="Compraretis service: Order confirmation",
                    recipient=request.user.email,
                    content=content_for_user
                )
                send_email(
                    subject="Compraretis service: New order",
                    recipient=get_random_activ_admin().email,
                    content=content_for_admin
                )

                return Response(
                    {"status": "success"},
                    status=201
                )

        except ValueError:
            return Response(
                {"error": "Invalid value for the contact"},
                status=400
            )
        except Exception:
            return Response(
                {"error": f"Internal server error. "
                          f"If this happens again, please contact the administrator {get_random_superuser().email}"},
                status=500
            )
