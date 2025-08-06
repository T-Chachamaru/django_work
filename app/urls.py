from django.contrib import admin
from django.urls import path,include

from app.views import account, home, project, manage, wiki

urlpatterns = [
    path('send/sms/', account.send_sms, name='send_sms'),
    path('login/sms/', account.login_sms, name='login_sms'),
    path('register/',account.register, name='register'),
    path('login/',account.login, name='login'),
    path('image/code/',account.image_code, name='image_code'),
    path('logout/',account.logout, name='logout'),
    path('index/',home.index, name='index'),
    path('project/list/',project.project_list, name='project_list'),
    path('project/star/<str:project_type>/<int:project_id>/', project.project_star, name='project_star'),
    path('manage/<int:project_id>/',include([
        path('dashboard/', manage.dashboard, name='dashboard'),
        path('issues/', manage.issues, name='issues'),
        path('statistics/', manage.statistics, name='statistics'),
        path('file/', manage.file, name='file'),
        path('wiki/', wiki.wiki, name='wiki'),
        path('wiki/add/', wiki.wiki_add, name='wiki_add'),
        path('wiki/catalog/', wiki.wiki_catalog, name='wiki_catalog'),
        path('wiki/delete/<int:wiki_id>/', wiki.wiki_delete, name='wiki_delete'),
        path('wiki/edit/<int:wiki_id>/', wiki.wiki_edit, name='wiki_edit'),
        path('wiki/upload/', wiki.wiki_upload, name='wiki_upload'),
        path('setting/', manage.setting, name='setting'),
    ],None)),

]