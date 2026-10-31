from datetime import timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from config.testing import make_poll, make_user
from .models import Poll


class SlugTests(TestCase):

    def setUp(self):
        self.user = make_user()

    def test_reserved_slug_is_not_used(self):
        poll = make_poll(self.user, question='Create')

        self.assertEqual(poll.slug, 'create-poll')

        response = self.client.get(reverse('polls:poll_detail', args=[poll.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create')

    def test_embed_test_slug_is_reserved(self):
        self.assertEqual(
            make_poll(self.user, question='Embed Test').slug,
            'embed-test-poll'
        )

    def test_slugs_stay_unique(self):
        first = make_poll(self.user, question='Same question')
        second = make_poll(self.user, question='Same question')

        self.assertNotEqual(first.slug, second.slug)

    def test_non_ascii_question_gets_readable_slug(self):
        poll = make_poll(self.user, question='Quelle base de données préférez-vous ?')

        self.assertTrue(poll.slug.startswith('quelle-base-de-donnees'))

        urdu = make_poll(self.user, question='کون سا ڈیٹابیس بہتر ہے')
        self.assertRegex(urdu.slug, r'^[a-z0-9-]+$')
        self.assertNotEqual(urdu.slug, 'poll')


class PollOptionTests(TestCase):

    def test_options_are_ordered_by_creation(self):
        poll = make_poll(make_user(), options=('Zeta', 'Alpha', 'Mid'))

        self.assertEqual(
            [o.option_text for o in poll.options.all()],
            ['Zeta', 'Alpha', 'Mid']
        )


class PollCreateTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.url = reverse('polls:poll_create')

    def payload(self, **overrides):
        data = {
            'question': 'Best editor?',
            'description': '',
            'voting_type': 'multiple_choice',
            'expires_at': (timezone.now() + timedelta(days=2)).strftime(
                '%Y-%m-%dT%H:%M'
            ),
            'options-TOTAL_FORMS': '4',
            'options-INITIAL_FORMS': '0',
            'options-MIN_NUM_FORMS': '2',
            'options-MAX_NUM_FORMS': '1000',
            'options-0-option_text': 'Vim',
            'options-1-option_text': 'Emacs',
            'options-2-option_text': '',
            'options-3-option_text': '',
        }
        data.update(overrides)
        return data

    def test_requires_login(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_creates_poll_with_options(self):
        self.client.force_login(self.user)

        response = self.client.post(self.url, self.payload())

        poll = Poll.objects.get(question='Best editor?')
        self.assertRedirects(
            response, reverse('polls:poll_detail', args=[poll.slug])
        )
        self.assertEqual(poll.created_by, self.user)
        self.assertEqual(poll.options.count(), 2)

    def test_rejects_past_expiry(self):
        self.client.force_login(self.user)
        past = (timezone.now() - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')

        response = self.client.post(self.url, self.payload(expires_at=past))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Poll.objects.count(), 0)

    def test_requires_two_options(self):
        self.client.force_login(self.user)

        response = self.client.post(
            self.url, self.payload(**{'options-1-option_text': ''})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Poll.objects.count(), 0)

    @override_settings(TIME_ZONE='Asia/Karachi')
    def test_form_states_time_zone(self):
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertContains(response, 'Time zone: Asia/Karachi')


class PollListTests(TestCase):

    def test_list_is_paginated(self):
        user = make_user()
        for i in range(25):
            make_poll(user, question=f'Poll number {i}')

        first = self.client.get(reverse('polls:poll_list'))
        second = self.client.get(reverse('polls:poll_list') + '?page=2')

        self.assertEqual(len(first.context['polls']), 20)
        self.assertEqual(len(second.context['polls']), 5)

    def test_list_query_count_is_constant(self):
        user = make_user()
        for i in range(10):
            make_poll(user, question=f'Poll number {i}')

        with self.assertNumQueries(2):  # count + page of polls (joined)
            self.client.get(reverse('polls:poll_list'))


class ClosePollTests(TestCase):

    def setUp(self):
        self.owner = make_user('owner')
        self.other = make_user('other')
        self.poll = make_poll(self.owner)
        self.url = reverse('polls:poll_close', args=[self.poll.slug])

    def test_owner_can_close(self):
        self.client.force_login(self.owner)

        response = self.client.post(self.url)

        self.assertRedirects(
            response, reverse('polls:poll_detail', args=[self.poll.slug])
        )
        self.poll.refresh_from_db()
        self.assertTrue(self.poll.is_frozen)

    def test_other_users_cannot_close(self):
        self.client.force_login(self.other)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 403)
        self.poll.refresh_from_db()
        self.assertFalse(self.poll.is_frozen)

    def test_anonymous_visitors_are_sent_to_login(self):
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 302)
        self.poll.refresh_from_db()
        self.assertFalse(self.poll.is_frozen)

    def test_get_is_not_allowed(self):
        self.client.force_login(self.owner)

        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_close_button_only_shown_to_owner(self):
        detail = reverse('polls:poll_detail', args=[self.poll.slug])

        self.assertNotContains(self.client.get(detail), 'Close this poll')

        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(detail), 'Close this poll')

        self.client.force_login(self.owner)
        self.assertContains(self.client.get(detail), 'Close this poll')


class EmbedTests(TestCase):

    def setUp(self):
        self.poll = make_poll(make_user())

    def test_embed_can_be_framed_by_other_sites(self):
        response = self.client.get(
            reverse('polls:poll_embed', args=[self.poll.slug])
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('X-Frame-Options', response.headers)
        self.assertIn('frame-ancestors *', response.headers['Content-Security-Policy'])
        # The rest of the policy is untouched.
        self.assertIn("script-src 'self'", response.headers['Content-Security-Policy'])

    def test_regular_pages_still_refuse_framing(self):
        response = self.client.get(
            reverse('polls:poll_detail', args=[self.poll.slug])
        )

        self.assertEqual(response.headers['X-Frame-Options'], 'DENY')
        self.assertIn(
            "frame-ancestors 'self'", response.headers['Content-Security-Policy']
        )

    def test_embed_links_to_poll_instead_of_fake_form(self):
        response = self.client.get(
            reverse('polls:poll_embed', args=[self.poll.slug])
        )

        self.assertNotContains(response, '<form')
        self.assertContains(
            response, reverse('voting:poll_vote', args=[self.poll.slug])
        )

    def test_embed_test_page_is_debug_only(self):
        url = reverse('polls:embed_test')

        self.assertEqual(self.client.get(url).status_code, 404)

        with override_settings(DEBUG=True):
            self.assertEqual(self.client.get(url).status_code, 200)


class NavigationAndSharingTests(TestCase):

    def setUp(self):
        self.owner = make_user('owner')
        self.poll = make_poll(self.owner)
        self.detail = reverse('polls:poll_detail', args=[self.poll.slug])

    def test_detail_links_to_live_results(self):
        response = self.client.get(self.detail)

        self.assertContains(
            response, reverse('results:poll_results', args=[self.poll.slug])
        )

    def test_detail_shows_share_link_and_embed_code(self):
        response = self.client.get(self.detail)

        self.assertContains(response, f'http://testserver{self.detail}')
        embed_path = reverse('polls:poll_embed', args=[self.poll.slug])
        # The iframe snippet is shown as escaped text, ready to copy.
        self.assertContains(response, '&lt;iframe src=&quot;http://testserver' + embed_path)

    def test_list_links_to_results_and_login_for_visitors(self):
        response = self.client.get(reverse('polls:poll_list'))

        self.assertContains(response, reverse('accounts:login'))
        self.assertContains(response, reverse('accounts:register'))
        self.assertContains(
            response, reverse('results:poll_results', args=[self.poll.slug])
        )
        self.assertNotContains(response, reverse('polls:poll_create'))

    def test_list_offers_create_poll_when_logged_in(self):
        self.client.force_login(self.owner)

        response = self.client.get(reverse('polls:poll_list'))

        self.assertContains(response, reverse('polls:poll_create'))
