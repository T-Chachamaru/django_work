from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods

from app import models
from utils.tencent.cos import CosManager

def setting(request, project_id):
    """
    渲染项目设置的主页面。

    这个视图目前只负责展示一个静态页面，不包含复杂的后端逻辑。
    """
    return render(request, 'app/setting.html')

@require_http_methods(["GET", "POST"])
def setting_delete(request, project_id):
    """
    处理删除项目的视图，包含用户确认逻辑。
    - GET: 显示删除确认页面，要求用户输入项目名称。
    - POST: 验证用户输入和权限，然后执行删除操作。
    """
    context = {}
    current_project = request.tracer.project
    if request.method == 'POST':
        project_name = request.POST.get('project_name', "").strip()
        if not project_name or project_name != current_project.name:
            context['error'] = "项目名称输入错误，请重新确认。"
            return render(request, 'app/setting_delete.html', context)
        if request.tracer.user != current_project.creator:
            context['error'] = "权限不足，只有项目创建者才能执行此操作。"
            return render(request, 'app/setting_delete.html', context)
        try:
            cos_client = CosManager(region=current_project.region)
            cos_client.delete_bucket(bucket=current_project.bucket)
        except Exception as e:
            context['error'] = "删除云存储桶失败，请联系管理员处理。"
            return render(request, 'app/setting_delete.html', context)
        models.Project.objects.filter(id=project_id).delete()

        return redirect("project_list")

    return render(request, 'app/setting_delete.html', context)