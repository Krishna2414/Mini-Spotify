from django.urls import path

from . import views

urlpatterns = [
    path("upload/", views.TrackCreateView.as_view(), name="track_create"),
    path("<int:pk>/", views.TrackDetailView.as_view(), name="track_detail"),
]
