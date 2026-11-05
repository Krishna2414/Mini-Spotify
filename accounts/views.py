from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProfileForm, SignUpForm


def home(request):
    return render(request, "home.html")


def signup(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f"Welcome, {user.username}! Your account is ready.")
        return redirect("home")
    return render(request, "registration/signup.html", {"form": form})


def profile_detail(request, username):
    profile_user = get_object_or_404(User, username=username)
    return render(request, "accounts/profile_detail.html", {"profile_user": profile_user})


@login_required
def profile_edit(request):
    profile = request.user.profile
    form = ProfileForm(request.POST or None, request.FILES or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect("profile_detail", username=request.user.username)
    return render(request, "accounts/profile_form.html", {"form": form})


@login_required
def account_delete(request):
    if request.method == "POST":
        user = request.user
        logout(request)
        user.delete()
        messages.info(request, "Your account has been deleted.")
        return redirect("home")
    return render(request, "accounts/account_confirm_delete.html")
