from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import TrackForm
from .models import Track


class TrackListView(ListView):
    model = Track
    paginate_by = 12
    context_object_name = "tracks"


class TrackDetailView(DetailView):
    model = Track
    context_object_name = "track"


class TrackCreateView(LoginRequiredMixin, CreateView):
    model = Track
    form_class = TrackForm

    def form_valid(self, form):
        form.instance.uploaded_by = self.request.user
        messages.success(self.request, "Track uploaded.")
        return super().form_valid(form)


class OwnerRequiredMixin(UserPassesTestMixin):
    """Only the user who uploaded the track may continue;
    everyone else gets 403."""

    def test_func(self):
        return self.get_object().uploaded_by == self.request.user


class TrackUpdateView(LoginRequiredMixin, OwnerRequiredMixin, UpdateView):
    model = Track
    form_class = TrackForm

    def form_valid(self, form):
        messages.success(self.request, "Track updated.")
        return super().form_valid(form)


class TrackDeleteView(LoginRequiredMixin, OwnerRequiredMixin, DeleteView):
    model = Track
    success_url = reverse_lazy("track_list")

    def form_valid(self, form):
        messages.success(self.request, f'"{self.object.title}" was deleted.')
        return super().form_valid(form)
