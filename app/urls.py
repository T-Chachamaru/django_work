from django.contrib import admin
from django.urls import path,include

from app.views import account, home

urlpatterns = [
    path('send/sms/', account.send_sms, name='send_sms'),
    path('login/sms/', account.login_sms, name='login_sms'),
    path('register/',account.register, name='register'),
    path('login/',account.login, name='login'),
    path('image/code/',account.image_code, name='image_code'),
    path('logout/',account.logout, name='logout'),
    path('index/',home.index, name='index'),
]