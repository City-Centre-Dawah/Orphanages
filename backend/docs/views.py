from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render


@staff_member_required
def user_manual(request):
    return render(request, "docs/user_manual.html")


@staff_member_required
def onboarding(request):
    return render(request, "docs/onboarding.html")


@staff_member_required
def troubleshooting(request):
    return render(request, "docs/troubleshooting.html")
