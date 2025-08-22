from django.utils.safestring import mark_safe

class Pagination:
    """
    一个通用的分页组件，用于生成分页导航的HTML。
    在视图函数中使用示例:

    from utils.pagination import Pagination

    def some_list_view(request):
        # 1. 获取数据
        queryset = YourModel.objects.all()

        # 2. 实例化分页对象
        page_obj = Pagination(
            current_page=request.GET.get('page'),
            all_count=queryset.count(),
            base_url=request.path_info,
            query_params=request.GET,
            per_page=10,
            pager_page_count=11
        )

        # 3. 对数据进行切片
        data_list = queryset[page_obj.start:page_obj.end]

        # 4. 将分页HTML和数据传递给模板
        return render(request, 'your_template.html', {
            'data_list': data_list,
            'page_html': page_obj.page_html()
        })
    """

    def __init__(self, current_page, all_count, base_url, query_params, per_page=30, pager_page_count=11):
        """
        初始化分页器
        :param current_page: 当前页码
        :param all_count: 数据总条数
        :param base_url: URL前缀，例如 request.path_info
        :param query_params: URL中携带的参数，例如 request.GET
        :param per_page: 每页显示的数据条数
        :param pager_page_count: 页面上最多显示的页码数量（建议为奇数）
        """
        self.base_url = base_url
        self.query_params = query_params.copy()  # 复制一份，避免污染原始数据
        self.query_params._mutable = True

        try:
            self.current_page = int(current_page)
            if self.current_page <= 0:
                self.current_page = 1
        except (TypeError, ValueError):
            self.current_page = 1

        self.per_page = per_page
        self.all_count = all_count
        self.pager_page_count = pager_page_count

        total_pages, remainder = divmod(all_count, per_page)
        if remainder:
            total_pages += 1
        self.total_pages = total_pages

        self.half_pager_count = self.pager_page_count // 2

    @property
    def start(self):
        """计算当前页数据的起始索引（用于数据库切片）"""
        return (self.current_page - 1) * self.per_page

    @property
    def end(self):
        """计算当前页数据的结束索引（用于数据库切片）"""
        return self.current_page * self.per_page

    def _build_url(self, page):
        """内部方法，用于生成带页码参数的URL"""
        self.query_params['page'] = page
        return f'{self.base_url}?{self.query_params.urlencode()}'

    def _get_page_range(self):
        """内部方法，计算要在页面上显示的页码范围"""
        # 情况1：总页数小于等于要显示的页码数，则显示所有页码
        if self.total_pages <= self.pager_page_count:
            return 1, self.total_pages

        # 情况2：总页数大于要显示的页码数
        # 计算起始和结束页码
        start_page = self.current_page - self.half_pager_count
        end_page = self.current_page + self.half_pager_count

        # 处理边界情况：当前页靠近首页时
        if start_page <= 1:
            start_page = 1
            end_page = self.pager_page_count

        # 处理边界情况：当前页靠近尾页时
        elif end_page >= self.total_pages:
            end_page = self.total_pages
            start_page = self.total_pages - self.pager_page_count + 1

        return start_page, end_page

    def page_html(self):
        """生成分页导航的完整HTML"""
        if self.all_count == 0:
            return ""

        page_list = []

        if self.current_page > 1:
            prev = f'<li><a href="{self._build_url(self.current_page - 1)}">上一页</a></li>'
        else:
            prev = '<li class="disabled"><a href="#">上一页</a></li>'
        page_list.append(prev)

        start, end = self._get_page_range()
        for i in range(start, end + 1):
            if self.current_page == i:
                tpl = f'<li class="active"><a href="{self._build_url(i)}">{i}</a></li>'
            else:
                tpl = f'<li><a href="{self._build_url(i)}">{i}</a></li>'
            page_list.append(tpl)

        if self.current_page < self.total_pages:
            nex = f'<li><a href="{self._build_url(self.current_page + 1)}">下一页</a></li>'
        else:
            nex = '<li class="disabled"><a href="#">下一页</a></li>'
        page_list.append(nex)

        info = f'<li class="disabled"><a>共{self.all_count}条数据，{self.current_page}/{self.total_pages}页</a></li>'
        page_list.append(info)

        return mark_safe("".join(page_list))