from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from config.testing import make_user


class RegistrationTests(TestCase):

    def payload(self, **overrides):
        data = {
            'username': 'newuser',
            'first_name': 'New',
            'last_name': 'User',
            'email': 'new@example.com',
            'password1': 'a-Long-Passw0rd!',
            'password2': 'a-Long-Passw0rd!',
        }
        data.update(overrides)
        return data

    def test_register_creates_user(self):
        response = self.client.post(reverse('accounts:register'), self.payload())

        self.assertRedirects(response, reverse('accounts:login'))
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_duplicate_email_is_rejected_case_insensitively(self):
        User.objects.create_user('existing', 'new@example.com', 'x')

        response = self.client.post(
            reverse('accounts:register'),
            self.payload(email='NEW@example.com')
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='newuser').exists())


class LoginTests(TestCase):

    def setUp(self):
        cache.clear()
        self.user = make_user('alice')
        self.url = reverse('accounts:login')

    def login(self, password='TestPassword123!', **extra):
        return self.client.post(
            self.url,
            {'username': 'alice', 'password': password, **extra}
        )

    def test_successful_login(self):
        response = self.login()

        self.assertRedirects(
            response, reverse('polls:poll_list'), fetch_redirect_response=False
        )

    def test_next_url_is_followed_when_local(self):
        response = self.login(next='/polls/create/')

        self.assertEqual(response['Location'], '/polls/create/')

    def test_next_url_to_other_site_is_ignored(self):
        response = self.login(next='https://evil.example/')

        self.assertEqual(response['Location'], reverse('polls:poll_list'))

    @override_settings(LOGIN_MAX_FAILURES=3)
    def test_lockout_after_repeated_failures(self):
        for _ in range(3):
            self.assertEqual(self.login('wrong').status_code, 200)

        locked = self.login('wrong')
        self.assertEqual(locked.status_code, 429)

        # Even the right password is refused during the lockout...
        self.assertEqual(self.login().status_code, 429)
        self.assertNotIn('_auth_user_id', self.client.session)

    @override_settings(LOGIN_MAX_FAILURES=3)
    def test_lockout_is_per_username(self):
        for _ in range(3):
            self.login('wrong')

        make_user('bob')
        response = self.client.post(
            self.url, {'username': 'bob', 'password': 'TestPassword123!'}
        )

        self.assertEqual(response.status_code, 302)

    @override_settings(LOGIN_MAX_FAILURES=3)
    def test_success_resets_failure_counter(self):
        self.login('wrong')
        self.login('wrong')
        self.login()  # success clears the counter
        self.client.post(reverse('accounts:logout'))

        for _ in range(2):
            self.assertEqual(self.login('wrong').status_code, 200)

    def test_logout_requires_post(self):
        self.client.force_login(self.user)

        self.assertEqual(self.client.get(reverse('accounts:logout')).status_code, 405)

        response = self.client.post(reverse('accounts:logout'))
        self.assertRedirects(response, reverse('accounts:login'))
