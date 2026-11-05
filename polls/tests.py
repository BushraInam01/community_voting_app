from datetime import timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from common.factories import make_poll, make_user
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


class EmbedHeightTests(TestCase):
    """The iframe height is calculated on the server (no JavaScript)."""

    def setUp(self):
        self.owner = make_user()

    def test_height_grows_with_number_of_options(self):
        few = make_poll(self.owner, question='Few', options=('A', 'B'))
        many = make_poll(
            self.owner, question='Many', options=tuple('ABCDEFGH')
        )

        self.assertEqual(many.embed_height - few.embed_height, 25 * 6)

    def test_height_accounts_for_description_and_closed_state(self):
        poll = make_poll(self.owner)
        base = poll.embed_height

        poll.description = 'Short description'
        self.assertEqual(poll.embed_height, base + 30)

        poll.is_frozen = True
        self.assertEqual(poll.embed_height, base + 60)

    def test_long_question_gets_extra_lines(self):
        short = make_poll(self.owner, question='Short?')
        long_ = make_poll(self.owner, question='Why ' * 40)

        self.assertGreater(long_.embed_height, short.embed_height)

    def test_four_option_poll_is_a_sensible_size(self):
        poll = make_poll(self.owner, options=('A', 'B', 'C', 'D'))

        # Old fixed height was 300px, which left a large blank area.
        self.assertLess(poll.embed_height, 250)
        self.assertGreater(poll.embed_height, 150)

    def test_share_snippet_uses_calculated_height_and_no_script(self):
        poll = make_poll(self.owner, options=('A', 'B', 'C', 'D'))

        response = self.client.get(
            reverse('polls:poll_detail', args=[poll.slug])
        )

        self.assertContains(response, f'height=&quot;{poll.embed_height}&quot;')
        self.assertNotContains(response, '&lt;script')

    def test_embed_test_page_uses_calculated_height(self):
        poll = make_poll(self.owner)

        with override_settings(DEBUG=True):
            response = self.client.get(reverse('polls:embed_test'))

        self.assertContains(response, f'height="{poll.embed_height}"')

    def test_embed_page_uses_compact_css_and_no_javascript(self):
        poll = make_poll(self.owner)

        response = self.client.get(
            reverse('polls:poll_embed', args=[poll.slug])
        )

        self.assertContains(response, '/static/css/embed.css')
        self.assertNotContains(response, '<script')


class OptionValidationTests(TestCase):
    """Options must be different, and a poll may have at most 10."""

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.url = reverse('polls:poll_create')

    def payload(self, options):
        data = {
            'question': 'Best editor?',
            'description': '',
            'voting_type': 'multiple_choice',
            'expires_at': (timezone.now() + timedelta(days=2)).strftime(
                '%Y-%m-%dT%H:%M'
            ),
            'options-TOTAL_FORMS': str(len(options)),
            'options-INITIAL_FORMS': '0',
            'options-MIN_NUM_FORMS': '2',
            'options-MAX_NUM_FORMS': '10',
        }
        for index, text in enumerate(options):
            data[f'options-{index}-option_text'] = text
        return data

    def test_repeated_options_are_rejected_ignoring_case_and_spaces(self):
        response = self.client.post(self.url, self.payload(['Yes', 'Yes', 'yes']))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Each option must be different')
        self.assertEqual(Poll.objects.count(), 0)

        response = self.client.post(self.url, self.payload(['Vim', ' VIM ']))

        self.assertEqual(Poll.objects.count(), 0)

    def test_blank_extra_options_are_not_counted_as_duplicates(self):
        response = self.client.post(
            self.url, self.payload(['Vim', 'Emacs', '', '', ''])
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Poll.objects.get().options.count(), 2)

    def test_ten_options_are_allowed(self):
        response = self.client.post(
            self.url, self.payload([f'Option {i}' for i in range(10)])
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Poll.objects.get().options.count(), 10)

    def test_more_than_ten_options_are_rejected(self):
        response = self.client.post(
            self.url, self.payload([f'Option {i}' for i in range(11)])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Poll.objects.count(), 0)

    def test_absurd_number_of_forms_is_rejected_without_creating_anything(self):
        response = self.client.post(
            self.url, self.payload([f'Option {i}' for i in range(300)])
        )

        self.assertIn(response.status_code, (200, 400))
        self.assertEqual(Poll.objects.count(), 0)


class SharedLayoutTests(TestCase):
    """Every page uses base.html: lang, viewport, navigation, messages."""

    def setUp(self):
        self.user = make_user()
        self.poll = make_poll(self.user)

    def pages(self):
        return [
            reverse('home'),
            reverse('polls:poll_list'),
            reverse('polls:poll_detail', args=[self.poll.slug]),
            reverse('results:results_list'),
            reverse('results:poll_results', args=[self.poll.slug]),
            reverse('accounts:login'),
            reverse('accounts:register'),
        ]

    def test_every_page_has_lang_viewport_and_stylesheet(self):
        for url in self.pages():
            response = self.client.get(url)

            self.assertContains(response, '<html lang="en">', msg_prefix=url)
            self.assertContains(response, 'name="viewport"', msg_prefix=url)
            self.assertContains(response, '/static/css/base.css', msg_prefix=url)

    def test_home_is_the_public_poll_list(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.poll.question)

    def test_navigation_for_visitors_and_logged_in_users(self):
        visitor = self.client.get(reverse('home'))

        self.assertContains(visitor, reverse('accounts:login'))
        self.assertContains(visitor, reverse('accounts:register'))
        self.assertNotContains(visitor, 'Logout')

        self.client.force_login(self.user)
        member = self.client.get(reverse('home'))

        self.assertContains(member, f'Logout ({self.user.username})')
        self.assertContains(member, reverse('polls:poll_create'))
        self.assertNotContains(member, reverse('accounts:register'))

    def test_messages_are_shown_once_in_the_shared_layout(self):
        voter = make_user('voter')
        self.client.force_login(voter)
        option = self.poll.options.first()

        response = self.client.post(
            reverse('voting:poll_vote', args=[self.poll.slug]),
            {'option': option.id},
            follow=True,
        )

        self.assertContains(response, 'Your vote has been submitted.', count=1)

    def test_results_page_still_polls_and_disables_htmx_eval(self):
        response = self.client.get(
            reverse('results:poll_results', args=[self.poll.slug])
        )

        self.assertContains(response, 'hx-trigger="every 3s"')
        self.assertContains(response, '"allowEval": false')

    def test_no_inline_scripts_or_styles_anywhere(self):
        import re

        for url in self.pages():
            html = self.client.get(url).content.decode()

            self.assertNotRegex(html, r'<script(?![^>]*\bsrc=)', msg=url)
            self.assertNotIn(' style="', html, msg=url)
            self.assertIsNone(re.search(r'<style[\s>]', html), url)


class OptionBoxRulesTests(TestCase):
    """Inner spaces count as one, and any two boxes may be filled."""

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.url = reverse('polls:poll_create')

    def payload(self, options):
        data = {
            'question': 'Best editor?',
            'description': '',
            'voting_type': 'multiple_choice',
            'expires_at': (timezone.now() + timedelta(days=2)).strftime(
                '%Y-%m-%dT%H:%M'
            ),
            'options-TOTAL_FORMS': str(len(options)),
            'options-INITIAL_FORMS': '0',
            'options-MIN_NUM_FORMS': '0',
            'options-MAX_NUM_FORMS': '10',
        }
        for index, text in enumerate(options):
            data[f'options-{index}-option_text'] = text
        return data

    def test_inner_whitespace_does_not_hide_a_duplicate(self):
        response = self.client.post(
            self.url, self.payload(['Yes please', 'Yes  please'])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Each option must be different')
        self.assertEqual(Poll.objects.count(), 0)

    def test_tabs_and_newlines_count_as_spaces_too(self):
        response = self.client.post(
            self.url, self.payload(['Yes please', 'yes\tplease'])
        )

        self.assertEqual(Poll.objects.count(), 0)

    def test_option_text_is_saved_with_single_spaces(self):
        self.client.post(
            self.url, self.payload(['  Yes    please  ', 'No thanks'])
        )

        texts = list(Poll.objects.get().options.values_list('option_text', flat=True))
        self.assertEqual(texts, ['Yes please', 'No thanks'])

    def test_any_two_boxes_may_be_filled(self):
        # Boxes 1 and 3 filled, box 2 left empty: allowed.
        response = self.client.post(
            self.url, self.payload(['Vim', '', 'Emacs', '', '', ''])
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Poll.objects.get().options.count(), 2)

    def test_one_filled_box_is_not_enough(self):
        response = self.client.post(
            self.url, self.payload(['Vim', '', '', '', '', ''])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please provide at least 2 options')
        self.assertEqual(Poll.objects.count(), 0)

    def test_no_filled_boxes_is_rejected(self):
        response = self.client.post(self.url, self.payload([''] * 6))

        self.assertContains(response, 'Please provide at least 2 options')
        self.assertEqual(Poll.objects.count(), 0)

    def test_form_shows_six_boxes(self):
        response = self.client.get(self.url)

        self.assertEqual(len(response.context['option_formset'].forms), 6)


class FaviconTests(TestCase):
    """Pages declare an icon, so browsers do not request /favicon.ico (404)."""

    def setUp(self):
        self.poll = make_poll(make_user())

    def test_regular_pages_link_to_the_favicon(self):
        for url in (
            reverse('home'),
            reverse('polls:poll_detail', args=[self.poll.slug]),
            reverse('results:poll_results', args=[self.poll.slug]),
            reverse('accounts:login'),
        ):
            response = self.client.get(url)

            self.assertContains(
                response, '/static/img/favicon.svg', msg_prefix=url
            )

    def test_embed_page_links_to_the_favicon(self):
        response = self.client.get(
            reverse('polls:poll_embed', args=[self.poll.slug])
        )

        self.assertContains(response, '/static/img/favicon.svg')

    def test_favicon_file_exists_and_is_valid_svg(self):
        from xml.etree import ElementTree

        from django.contrib.staticfiles import finders

        path = finders.find('img/favicon.svg')

        self.assertIsNotNone(path)
        self.assertTrue(ElementTree.parse(path).getroot().tag.endswith('svg'))

    def test_favicon_is_allowed_by_the_csp(self):
        # img-src 'self' covers a same-origin icon; nothing needs relaxing.
        response = self.client.get(reverse('home'))

        self.assertIn("img-src 'self'", response.headers['Content-Security-Policy'])
