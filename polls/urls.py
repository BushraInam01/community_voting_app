from django.urls import path

from .views import (
    PollCloseView,
    PollCreateView,
    PollDetailView,
    PollEmbedTestView,
    PollEmbedView,
    PollListView,
)

app_name = 'polls'

# NOTE: fixed routes must stay above '<slug:slug>/'. polls/slugs.py reserves
# the matching slugs so a poll can never be given one of these names.
urlpatterns = [
    path('', PollListView.as_view(), name='poll_list'),
    path('create/', PollCreateView.as_view(), name='poll_create'),
    path('embed-test/', PollEmbedTestView.as_view(), name='embed_test'),
    path('embed/<slug:slug>/', PollEmbedView.as_view(), name='poll_embed'),
    path('<slug:slug>/close/', PollCloseView.as_view(), name='poll_close'),
    path('<slug:slug>/', PollDetailView.as_view(), name='poll_detail'),
]
