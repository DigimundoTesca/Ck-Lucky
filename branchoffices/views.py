from django.contrib.auth.decorators import login_required
from django.shortcuts import render


# -------------------------------------  Branch offices -------------------------------------
@login_required(login_url='users:login')
def branch_offices(request):
    template = 'branchoffices.html'
    context = {
        'page_title': 'Sucursales'
    }
    return render(request, template, context)
