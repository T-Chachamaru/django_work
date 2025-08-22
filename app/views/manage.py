from django.shortcuts import render

def dashboard(request, project_id):
    return render(request, 'app/dashboard.html')

def statistics(request, project_id):
    return render(request, 'app/statistics.html')
