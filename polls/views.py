from django.views import View
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.db import transaction
from django.views.decorators.clickjacking import xframe_options_exempt

from .models import Poll
from .forms import PollForm, PollOptionFormSet


class PollListView(View):

    def get(self, request):
        polls = Poll.objects.all().order_by('-created_at')

        context = {
            'polls': polls,
        }

        return render(request, 'polls/poll_list.html', context)


class PollDetailView(View):

    def get(self, request, slug):
        poll = get_object_or_404(
            Poll.objects.prefetch_related('options'),
            slug=slug
        )

        context = {
            'poll': poll,
        }

        return render(request, 'polls/poll_detail.html', context)


@method_decorator(xframe_options_exempt, name='dispatch')
class PollEmbedView(View):

    def get(self, request, slug):
        poll = get_object_or_404(
            Poll.objects.prefetch_related('options'),
            slug=slug
        )

        context = {
            'poll': poll,
        }

        return render(
            request,
            'polls/embed_poll.html',
            context
        )


@method_decorator(login_required, name='dispatch')
class PollCreateView(View):

    def get(self, request):
        poll_form = PollForm()
        option_formset = PollOptionFormSet()

        context = {
            'poll_form': poll_form,
            'option_formset': option_formset,
        }

        return render(request, 'polls/poll_create.html', context)

    def post(self, request):
        poll_form = PollForm(request.POST)
        option_formset = PollOptionFormSet(request.POST)

        if poll_form.is_valid() and option_formset.is_valid():

            with transaction.atomic():
                poll = poll_form.save(commit=False)
                poll.created_by = request.user
                poll.save()

                option_formset.instance = poll
                option_formset.save()

            return redirect(
                'polls:poll_detail',
                slug=poll.slug
            )

        context = {
            'poll_form': poll_form,
            'option_formset': option_formset,
        }

        return render(request, 'polls/poll_create.html', context)



class PollEmbedTestView(View):

    def get(self, request):
        return render(
            request,
            'polls/embed_test.html'
        )