from django.contrib import admin
from django.urls import path, include

from app.views import account, home, project, manage, wiki, file, setting, issues

# --------------------------------------------------------------------------------
# 定义项目管理内部的URL列表
# 将所有 /manage/<int:project_id>/... 相关的路由集中在这里
# --------------------------------------------------------------------------------
project_manage_patterns = [
    # Dashboard 和 统计
    path('dashboard/', manage.dashboard, name='dashboard'),
    path('statistics/', manage.statistics, name='statistics'),

    # 问题管理 (Issues)
    path('issues/', issues.issues, name='issues'),
    path('issues/detail/<int:issues_id>/', issues.issues_detail, name='issues_detail'),
    path('issues/record/<int:issues_id>/', issues.issues_record, name='issues_record'),

    # Wiki
    path('wiki/', wiki.wiki, name='wiki'),
    path('wiki/add/', wiki.wiki_add, name='wiki_add'),
    path('wiki/catalog/', wiki.wiki_catalog, name='wiki_catalog'),
    path('wiki/delete/<int:wiki_id>/', wiki.wiki_delete, name='wiki_delete'),
    path('wiki/edit/<int:wiki_id>/', wiki.wiki_edit, name='wiki_edit'),
    path('wiki/upload/', wiki.wiki_upload, name='wiki_upload'),

    # 文件管理 (File)
    path('file/', file.file, name='file'),
    path('file/delete/', file.file_delete, name='file_delete'),
    path('file/post/', file.file_post, name='file_post'),
    path('file/download/<int:file_id>/', file.file_download, name='file_download'),
    path('cos/cos_credential/', file.cos_credential, name='cos_credential'),

    # 项目设置 (Setting)
    path('setting/', setting.setting, name='setting'),
    path('setting/delete/', setting.setting_delete, name='setting_delete'),
]


# --------------------------------------------------------------------------------
# 定义主 URL 列表
# --------------------------------------------------------------------------------
urlpatterns = [
    # 账户相关 (Account)
    path('register/', account.register, name='register'),
    path('login/', account.login, name='login'),
    path('login/sms/', account.login_sms, name='login_sms'),
    path('logout/', account.logout, name='logout'),
    path('image/code/', account.image_code, name='image_code'),
    path('send/sms/', account.send_sms, name='send_sms'),

    # 首页 (Home)
    path('index/', home.index, name='index'),

    # 项目列表 (Project)
    path('project/list/', project.project_list, name='project_list'),
    path('project/star/<str:project_type>/<int:project_id>/', project.project_star, name='project_star'),

    # 项目管理 (Manage) - 包含上述定义的所有子路由
    path('manage/<int:project_id>/', include(project_manage_patterns)),
]