from django.urls import include, path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("accounts/signup/", views.signup, name="signup"),
    path("accounts/profile/edit/", views.profile_edit, name="profile_edit"),
    path("accounts/delete/", views.account_delete, name="account_delete"),
    path("accounts/", include("django.contrib.auth.urls")),  # login, logout
    path("profile/<str:username>/", views.profile_detail, name="profile_detail"),
]
