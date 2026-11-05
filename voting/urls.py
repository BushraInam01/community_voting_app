from django.urls import path

from .views import PollVoteView

app_name = 'voting'

urlpatterns = [
    path('<slug:slug>/vote/', PollVoteView.as_view(), name='poll_vote'),
]