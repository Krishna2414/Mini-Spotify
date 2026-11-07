from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, DetailView, ListView

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
