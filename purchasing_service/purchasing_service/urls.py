"""
URL configuration for purchasing_service project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from backend.authentication import custom_obtain_auth_token
from backend.views import (data_import, user_register, user_register_confirm,
                           ShopListView, ProductListView, BasketAPIView,
                           ContactAPIView, OrderAPIView, UserDetailsListView,
                           CategoriesListView)
from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/partner/data_import', data_import),
    path('api/v1/user/register', user_register),
    path('api/v1/user/register/confirm', user_register_confirm),
    path('api/v1/user/', include('django_rest_passwordreset.urls')),
    path('api/v1/user/login', custom_obtain_auth_token),
    path('api/v1/user/details', UserDetailsListView.as_view()),
    path('api/v1/user/contact', ContactAPIView.as_view()),
    path('api/v1/shops', ShopListView.as_view()),
    path('api/v1/categories', CategoriesListView.as_view()),
    path('api/v1/products', ProductListView.as_view()),
    path('api/v1/basket', BasketAPIView.as_view()),
    path('api/v1/order', OrderAPIView.as_view()),
]
