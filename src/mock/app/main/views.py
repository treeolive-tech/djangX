# ramani: src/mock/app/main/views.py
from django.shortcuts import render


def index(request):
    return render(request, "bootstrap/index.html", {})
