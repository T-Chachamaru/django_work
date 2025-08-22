from app import models

class CheckFilter:
    def __init__(self, allowed_filters, request):
        self.allowed_filters = allowed_filters
        self.request = request

    def get_query_conditions(self):
        """根据URL参数生成数据库查询条件"""
        conditions = {}
        for param in self.allowed_filters:
            value = self.request.GET.get(param)
            if value:
                conditions[f"{param}_id"] = value
        return conditions

    def get_filter_choices(self):
        """为模板生成所有筛选器的选项、URL和激活状态"""
        project = self.request.tracer.project
        filter_choices = {
            '状态': self._build_choices('status', models.Issues.status_choices),
            '优先级': self._build_choices('priority', models.Issues.priority_choices),
            '指派人': self._build_choices('assign', self._get_project_members(project)),
            '关注者': self._build_choices('attention', self._get_project_members(project)),
        }
        return filter_choices

    def _build_choices(self, param_name, choices_data):
        query_params = self.request.GET.copy()
        current_value = query_params.get(param_name)
        option_list = []
        query_params.pop(param_name, None)
        option_list.append({
            'text': '全部',
            'url': f"?{query_params.urlencode()}",
            'active': not current_value
        })

        for key, text in choices_data:
            query_params[param_name] = key
            option_list.append({
                'text': text,
                'url': f"?{query_params.urlencode()}",
                'active': str(key) == current_value
            })

        return option_list

    def _get_project_members(self, project):
        """获取项目成员列表用于筛选"""
        members = [(project.creator.id, project.creator.username)]
        project_users = models.ProjectUser.objects.filter(project=project).values_list('user_id', 'user__username')
        members.extend(project_users)
        return members