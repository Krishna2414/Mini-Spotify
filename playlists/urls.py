from django.urls import path

from . import views

urlpatterns = [
    path("", views.playlist_list, name="playlist_list"),          # used by navbar in base.html
    path("new/", views.playlist_create, name="playlist_create"),
    path("<int:pk>/", views.playlist_detail, name="playlist_detail"),
    path("add-track/<int:track_pk>/", views.add_track, name="add_track"),
    path("<int:pk>/remove/<int:track_pk>/", views.remove_track, name="remove_track"),
]