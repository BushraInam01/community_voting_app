from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csp import csp_override

from config.csp import embed_csp_config

from .forms import PollForm, PollOptionFormSet
from .models import Poll

POLLS_PER_PAGE = 20


class PollListView(View):

    def get(self, request):
        polls = Poll.objects.select_related('created_by').order_by(
            '-created_at'
        )

        page_obj = Paginator(polls, POLLS_PER_PAGE).get_page(
            request.GET.get('page')
        )

        context = {
            'polls': page_obj,
            'page_obj': page_obj,
        }

        return render(request, 'polls/poll_list.html', context)


class PollDetailView(View):

    def get(self, request, slug):
        poll = get_object_or_404(
            Poll.objects.select_related('created_by').prefetch_related(
                'options'
            ),
            slug=slug
        )

        share_url = request.build_absolute_uri(
            reverse('polls:poll_detail', args=[poll.slug])
        )

        embed_url = request.build_absolute_uri(
            reverse('polls:poll_embed', args=[poll.slug])
        )

        embed_code = (
            f'<iframe src="{embed_url}" width="600" '
            f'height="{poll.embed_height}" title="Community poll"></iframe>'
        )

        context = {
            'poll': poll,
            'share_url': share_url,
            'embed_code': embed_code,
            'can_close': (
                request.user.is_authenticated
                and request.user == poll.created_by
                and not poll.is_frozen
                and not poll.is_expired
            ),
        }

        return render(request, 'polls/poll_detail.html', context)


# The global CSP sends frame-ancestors 'self', which browsers enforce even
# when X-Frame-Options is removed. The embed view overrides the policy so it
# can be framed by the sites listed in EMBED_FRAME_ANCESTORS.
@method_decorator(xframe_options_exempt, name='dispatch')
@method_decorator(csp_override(embed_csp_config()), name='dispatch')
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


@method_decorator(login_required, name='dispatch')
class PollCloseView(View):
    """Lets a poll's creator close (freeze) it before its expiry date."""

    def post(self, request, slug):
        poll = get_object_or_404(Poll, slug=slug)

        if poll.created_by_id != request.user.id:
            return HttpResponseForbidden(
                'Only the poll creator can close this poll.'
            )

        if not poll.is_frozen:
            poll.is_frozen = True
            poll.save(update_fields=['is_frozen'])
            messages.success(request, 'The poll has been closed.')

        return redirect('polls:poll_detail', slug=poll.slug)


class PollEmbedTestView(View):
    """Development-only page for trying the embed iframe."""

    def get(self, request):
        if not settings.DEBUG:
            raise Http404

        poll = Poll.objects.order_by('-created_at').first()

        return render(
            request,
            'polls/embed_test.html',
            {'poll': poll}
        )
