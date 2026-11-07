from django.urls import path

from . import views

urlpatterns = [
    path("", views.TrackListView.as_view(), name="track_list"),
    path("upload/", views.TrackCreateView.as_view(), name="track_create"),
    path("<int:pk>/", views.TrackDetailView.as_view(), name="track_detail"),
]
