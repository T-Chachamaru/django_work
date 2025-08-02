import base
from app import models

def run():
    if not models.PricePolicy.objects.filter(category=1,title='个人免费版').exists():
        models.PricePolicy.objects.create(
            category=1,
            title='个人免费版',
            price=0,
            project_num=3,
            project_members=2,
            project_space=20,
            per_file_size=5,
        )

if __name__ == '__main__':
    run()