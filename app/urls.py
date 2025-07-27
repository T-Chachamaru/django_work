from django.contrib import admin
from django.urls import path,include

from app.views import account

urlpatterns = [
    path('send/sms/', account.send_sms, name='send_sms'),
    path('register/',account.register, name='register'),
]