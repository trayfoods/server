from django.shortcuts import render
from django.http import HttpResponse


def index_view(request):
    return render(request, "index.html")


def admin_ping(request):
    # return an 200 OK response
    return HttpResponse(status=200)
