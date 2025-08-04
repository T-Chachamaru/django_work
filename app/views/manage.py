from django.shortcuts import render

def dashboard(request, project_id):
    return render(request, 'app/dashboard.html')

def issues(request, project_id):
    return render(request, 'app/issues.html')

def statistics(request, project_id):
    return render(request, 'app/statistics.html')

def file(request, project_id):
    return render(request, 'app/file.html'
                           '')

def wiki(request, project_id):
    return render(request, 'app/wiki.html')

def setting(request, project_id):
    return render(request, 'app/setting.html')
