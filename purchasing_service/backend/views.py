import requests
import yaml
from django.core.validators import URLValidator, ValidationError
from django.db import IntegrityError, transaction
from requests.exceptions import ConnectionError, ConnectTimeout
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Category, ProductInfo, Parameter, ProductParameter, Shop, ShopCategory, Product


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
                        if category_obj and category_obj.name != name:
                            return Response(
                                {"error": f"This id={id} is already in use for the category - select another"},
                                status=400
                            )
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
