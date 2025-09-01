from app import models

class CheckFilter:
    """
    一个多功能的筛选器处理器，用于问题列表页面。
    它可以同时生成链接式筛选器和下拉选择式筛选器。
    """
    def __init__(self, allowed_filters, request):
        self.allowed_filters = allowed_filters
        self.request = request

    def get_query_conditions(self):
        """
        根据URL参数生成数据库查询条件。
        (已修正此处的逻辑)
        """
        conditions = {}
        for param in self.allowed_filters:
            value = self.request.GET.get(param)
            if value:
                # 只有当字段是外键或多对多关系时，才可能需要加_id或特殊处理。
                # 对于status和priority这种普通字段，直接使用字段名。
                if param in ['status', 'priority']:
                    conditions[param] = value
                elif param == 'attention':
                    # 'attention' 是多对多字段，查询键直接是字段名
                    conditions[param] = value
                else:
                    # 其他（如assign）是外键，需要加_id后缀
                    conditions[f"{param}_id"] = value
        return conditions

    def get_filter_choices(self):
        """为模板准备所有筛选器的选项数据。"""
        project = self.request.tracer.project
        members = self._get_project_members(project)

        filter_choices = {
            'status': self._build_check_choices('status', models.Issues.status_choices),
            'priority': self._build_check_choices('priority', models.Issues.priority_choices),
            'assign': self._build_select_options('assign', members),
            'attention': self._build_select_options('attention', members),
        }
        return filter_choices

    def _build_check_choices(self, param_name, choices_data):
        """为链接式筛选器（如状态、优先级）构建选项。"""
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

    def _build_select_options(self, param_name, choices_data):
        """为<select>下拉筛选器（如指派人）构建选项。"""
        current_value = self.request.GET.get(param_name)
        option_list = []
        for key, text in choices_data:
            option_list.append({
                'value': key,
                'text': text,
                'selected': str(key) == current_value
            })
        return option_list

    def _get_project_members(self, project):
        """获取项目成员列表作为筛选选项。"""
        members = [(project.creator.id, project.creator.username)]
        project_users = models.ProjectUser.objects.filter(project=project).values_list('user_id', 'user__username')
        members.extend(project_users)
        return members
