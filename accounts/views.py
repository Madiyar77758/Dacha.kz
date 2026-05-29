from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import SignUpForm


def signup(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("home")
    else:
        form = SignUpForm()
    return render(request, "accounts/signup.html", {"form": form})


@login_required
def become_host(request):
    """Превращает обычного гостя в хоста одним кликом."""
    if request.method == "POST":
        request.user.is_host = True
        request.user.save(update_fields=["is_host"])
        return redirect("host_dashboard")
    return render(request, "accounts/become_host.html")
