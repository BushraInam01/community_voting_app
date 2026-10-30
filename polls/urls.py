from django.urls import path
from .views import (
    PollListView,
    PollDetailView,
    PollCreateView,
    PollEmbedView,
    PollEmbedTestView,
)

app_name = 'polls'

urlpatterns = [
    path('', PollListView.as_view(), name='poll_list'),
    path('create/', PollCreateView.as_view(), name='poll_create'),
    path('embed-test/', PollEmbedTestView.as_view(), name='embed_test'),
    path('embed/<slug:slug>/', PollEmbedView.as_view(), name='poll_embed'),
    path('<slug:slug>/', PollDetailView.as_view(), name='poll_detail'),
]