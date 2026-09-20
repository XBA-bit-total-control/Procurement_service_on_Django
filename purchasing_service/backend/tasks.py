from celery import shared_task
from django.core.mail import send_mail as django_message
from django.db import IntegrityError, transaction
from rest_framework.response import Response

from .models import (Category, ProductInfo, Parameter, Shop,
                     ProductParameter, ShopCategory, Product)
from .services import get_random_superuser


@shared_task
def send_email(
        subject: str,
        recipient: str,
        content: str
) -> bool:
    """Функция отправки email.

    Args:
        subject: тема письма
        recipient: получатель
        content: содержимое письма

    Returns:
        bool: True при успешной отправке.
    """
    django_message(
        subject=subject,
        message=content,
        from_email=None,
        recipient_list=[recipient],
        fail_silently=False
    )
    return True


@shared_task
def update_partner_price(
        user_id: int,
        dict_data: dict,
        for_celery: bool = False
) -> Response | dict:
    """Функция обновление прайса партнера.

    Args:
        user_id: идентификатор пользователя
        dict_data: данные для обновления
        for_celery: флаг для передачи celery

    Returns:
        Response: без передачи celery.
        dict: при передаче celery.
    """

    def check_changes_in_product_info(
            product_info_obj,
            name,
            model,
            price,
            price_rrc,
            quantity
    ) -> bool:
        """Внутренняя функция проверки наличия изменений в информации о продукте.

        Args:
            product_info_obj: QuerySet
            name: название
            model: модель
            price: цена
            price_rrc: розничная цена
            quantity: количество

        Returns:
            bool: True, если есть изменения, иначе False.
        """
        product_info_obj = product_info_obj.first()
        if product_info_obj.name != name:
            return True
        if model != "__не_передана__":
            if product_info_obj.model != model:
                return True
        if float(product_info_obj.price) != float(price):
            return True
        if price_rrc != "__не_передана__":
            if float(product_info_obj.price_rrc) != float(price_rrc):
                return True
        if product_info_obj.quantity != quantity:
            return True
        else:
            return False

    def execution(
            user_id_: int,
            dict_data_: dict,
    ) -> Response:
        """Внутренняя функция обработки данных.

        При успешной и обработке с результатом предоставляется
        отчет пользователю о выполнении операции.

        Args:
            user_id_: идентификатор пользователя
            dict_data_: словарь с данными

        Returns:
            Response: сформированный ответ.
        """
        # Создание переменной для ответа-отчета
        response_report = Response(data={"status": "success"})
        response_report.status_code = 201

        categories = dict_data_.get("categories")
        goods = dict_data_.get("goods")
        shop = dict_data_.get("shop")
        # Указание магазина необязательно, но если он указан и не принадлежит
        # пользователю, то выбрасывается исключение
        if shop:
            shop_obj = Shop.objects.filter(name=shop).first()
            if shop_obj is None:
                return Response(
                    {"error": f"The specified store '{shop}' does not exist"},
                    status=404
                )
            if shop_obj.user.id != user_id_:
                return Response(
                    {"error": f"{shop} store does not belong to you"},
                    status=403
                )
        else:
            shop_obj = Shop.objects.filter(user_id=user_id_).first()
            if shop_obj is None:
                return Response(
                    {"error": "There is no store owned by you"},
                    status=404
                )
        # Проверка на наличие данных для импорта
        if categories is None and goods is None:
            return Response(
                {"error": "There is no record data in the provided URL information"},
                status=400
            )
        try:
            with transaction.atomic():  # Защита от неполного импорта
                if categories:
                    response_report.data["created_categories"] = 0  # Отчетность
                    # Блок обработки категорий
                    for category in categories:
                        id = category.get("id")
                        name = category.get("name")
                        if name is None:
                            raise AssertionError("The required category name was not "
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
                                    created = False
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
                            response_report.data["created_categories"] += 1  # Отчетность

                    # При отсутствии созданных категорий, удаляется ключ в отчете
                    if response_report.data["created_categories"] == 0:
                        response_report.data.pop("created_categories")

                if goods:
                    # Формирование полей для ответа-отчета
                    response_report.data["created_product_information"] = 0
                    response_report.data["updated_product_information"] = 0
                    response_report.data["deleted_product_information"] = 0

                    response_report.data["created_product_parameters"] = 0
                    response_report.data["updated_product_parameters"] = 0
                    response_report.data["deleted_product_parameters"] = 0

                    # Блок обработки товаров
                    for good in goods:
                        # Указание категории допустимо идентификатором или названием
                        category = good.pop("category", None)
                        if category is None:
                            raise AssertionError("Product was not assigned a category attribute")
                        else:
                            if not isinstance(category, int | str):
                                raise AssertionError("The category attribute must be a string or a number")

                        # Указание идентификатора товара подразумевает его обновление
                        id = good.pop("id", None)
                        if id:
                            if not isinstance(id, int):
                                raise AssertionError("The id attribute must be a number")

                            product_info_obj = ProductInfo.objects.filter(
                                id=id,
                                shop=shop_obj
                            )
                            if not bool(product_info_obj):
                                raise AssertionError(f"Information about your product with id={id} does not exist"
                                                     f" - updating product information will not work")

                        model = good.get("model", "__не_передана__")
                        if model != "__не_передана__":
                            if not isinstance(model, str):
                                raise AssertionError("The model attribute must be a string")

                        name = good.get("name")
                        if name is None:
                            raise AssertionError("Product was not assigned a name attribute")
                        else:
                            if not isinstance(name, str):
                                raise AssertionError("The name attribute must be a string")

                        parameters = good.pop("parameters", None)
                        if parameters:
                            if not isinstance(parameters, dict):
                                raise AssertionError("The parameters attribute must be a dictionary")
                            for parameter, value in parameters.items():
                                if not isinstance(parameter, str):
                                    raise AssertionError("Parameter name/key must be a string")
                                if not isinstance(value, str | int | float | bool | None):
                                    raise AssertionError("Parameter value must be a string, number, or boolean")

                        price = good.get("price")
                        if price is None:
                            raise AssertionError("Product was not assigned a price attribute")
                        else:
                            if not isinstance(price, int | float):
                                raise AssertionError("The price attribute must be a number")
                            if price < 0:
                                raise AssertionError("The price attribute must be a positive number")

                        price_rrc = good.get("price_rrc", "__не_передана__")
                        if price_rrc != "__не_передана__":
                            if not isinstance(price_rrc, int | float):
                                raise AssertionError("The price_rrc attribute must be a number")
                            if price_rrc < 0:
                                raise AssertionError("The price_rrc attribute must be a positive number")

                        # Указание None для значения количества подразумевает сигнал на удаление
                        quantity = good.get("quantity")
                        if quantity is None and id is None:
                            raise AssertionError("You cannot delete product information that has not been created")
                        else:
                            if isinstance(quantity, int):
                                if quantity <= 0:
                                    raise AssertionError("The quantity attribute must be a positive number")
                            elif quantity is not None:
                                raise AssertionError("The quantity attribute must be a number")

                        if isinstance(category, int):
                            category_obj = Category.objects.filter(id=category).first()
                        else:
                            category_obj = Category.objects.filter(name=category).first()
                        if category_obj is None:
                            raise AssertionError(f"Category {f"with id={category}"
                            if isinstance(category, int) else f"'{category}'"} does not exist")

                        if id:
                            if quantity is None:  # Удаление информации о товаре
                                product_info_obj.delete()
                                response_report.data["deleted_product_information"] += 1  # Отчетность
                                continue
                            else:  # Обновление информации о товаре, при наличии изменений
                                if check_changes_in_product_info(product_info_obj, name, model,
                                                                 price, price_rrc, quantity):
                                    product_info_obj.update(**good)
                                    response_report.data["updated_product_information"] += 1  # Отчетность
                        else:  # Создание информации о товаре, если записи ещё нет
                            product_obj, created = Product.objects.get_or_create(
                                name=name,
                                category=category_obj,
                                defaults={"name": name, "category": category_obj}
                            )
                            check_existence = ProductInfo.objects.filter(
                                name=name,
                                shop=shop_obj
                            ).first()
                            if check_existence:
                                continue
                            product_info_obj = ProductInfo.objects.create(
                                **good,
                                shop=shop_obj,
                                product=product_obj
                            )
                            response_report.data["created_product_information"] += 1  # Отчетность

                        if parameters:
                            # Блок обработки параметров
                            for parameter, value in parameters.items():
                                if isinstance(value, bool):
                                    value = str(value)
                                parameter_obj, _ = Parameter.objects.get_or_create(
                                    name=parameter,
                                    defaults={"name": parameter}
                                )
                                # Указание None для значения существующего параметра подразумевает его удаление
                                if value is not None:
                                    if id:
                                        product_info_obj = ProductInfo.objects.filter(id=id).first()
                                    product_parameter_obj, created = ProductParameter.objects.get_or_create(
                                        product_info=product_info_obj,
                                        parameter=parameter_obj,
                                        defaults={
                                            "product_info": product_info_obj,
                                            "parameter": parameter_obj,
                                            "value": value
                                        }
                                    )
                                    if not created:  # Обновление при наличии изменений
                                        if product_parameter_obj.value != str(value):
                                            product_parameter_obj.value = value
                                            product_parameter_obj.save()
                                            response_report.data["updated_product_parameters"] += 1  # Отчетность
                                    else:  # Создание при отсутствии
                                        response_report.data["created_product_parameters"] += 1  # Отчетность
                                else:  # Удаление параметра
                                    product_parameter_obj = ProductParameter.objects.filter(
                                        product_info=product_info_obj,
                                        parameter=parameter_obj
                                    ).first()
                                    if product_parameter_obj is None:
                                        raise AssertionError(f"It is impossible to delete a parameter '{parameter}'"
                                                             " that does not exist")
                                    product_parameter_obj.delete()
                                    response_report.data["deleted_product_parameters"] += 1  # Отчетность

                    # Обработка и удаление пустых полей для ответа-отчета
                    if response_report.data["created_product_information"] == 0:
                        response_report.data.pop("created_product_information")
                    if response_report.data["updated_product_information"] == 0:
                        response_report.data.pop("updated_product_information")
                    if response_report.data["deleted_product_information"] == 0:
                        response_report.data.pop("deleted_product_information")
                    if response_report.data["created_product_parameters"] == 0:
                        response_report.data.pop("created_product_parameters")
                    if response_report.data["updated_product_parameters"] == 0:
                        response_report.data.pop("updated_product_parameters")
                    if response_report.data["deleted_product_parameters"] == 0:
                        response_report.data.pop("deleted_product_parameters")

                # Проверка на наличие изменений
                if len(response_report.data) == 1:
                    response_report.status_code = 200
                    response_report.data["msg"] = "No changes"
                return response_report

        # Блок обработки ошибок
        except AssertionError as err:
            return Response(
                {
                    "status": "fail",
                    "error": err.__str__()
                },
                status=400
            )
        except AttributeError:
            return Response(
                {
                    "status": "fail",
                    "error": "Please list the categories and products in the list,"
                             " even if there is only one item in it"
                },
                status=400
            )
        except IntegrityError:
            return Response(
                {"error": f"Data import error."
                          f" The request has been rejected due to a data conflict"},
                status=400
            )
        except Exception:
            return Response(
                {"error": f"Internal server error during data processing. "
                          f"If this happens again, please contact the administrator {get_random_superuser().email}"},
                status=500
            )

    # Возвращение результата в соответствии с установленным флагом для Celery
    result = execution(user_id, dict_data)
    if for_celery:
        return result.data
    else:
        return result
