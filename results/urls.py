from django.urls import path

from .views import PollResultsView, ResultsListView

app_name = 'results'

urlpatterns = [
    path('', ResultsListView.as_view(), name='results_list'),
    path('<slug:slug>/', PollResultsView.as_view(), name='poll_results'),
]