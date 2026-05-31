from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import redirect, render

from .forms import ProfileForm, SignUpForm


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


@login_required
def profile(request):
    """Профиль: редактирование данных и смена пароля на одной странице."""
    profile_form = ProfileForm(instance=request.user)
    password_form = PasswordChangeForm(request.user)

    if request.method == "POST":
        if "save_profile" in request.POST:
            profile_form = ProfileForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Профиль обновлён.")
                return redirect("profile")
        elif "change_password" in request.POST:
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)  # чтобы не разлогинило
                messages.success(request, "Пароль изменён.")
                return redirect("profile")

    return render(request, "accounts/profile.html", {
        "profile_form": profile_form,
        "password_form": password_form,
    })
