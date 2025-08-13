from django.contrib.auth.decorators import login_required
from django.shortcuts import render

# @login_required
def tab_bliss(request):
    return render(request, "bliss/tab_bliss.html")
