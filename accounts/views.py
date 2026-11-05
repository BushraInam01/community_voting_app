from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View

from . import throttle
from .forms import RegistrationForm


#Register view
class RegisterView(View):

    def get(self, request):

        if request.user.is_authenticated:
            return redirect('polls:poll_list')

        form = RegistrationForm()

        context = {
            'form': form,
        }

        return render(request, 'accounts/register.html', context)

    def post(self, request):

        if request.user.is_authenticated:
            return redirect('polls:poll_list')

        form = RegistrationForm(request.POST)

        if form.is_valid():

            form.save()

            messages.success(
                request,
                'Your account has been created successfully. Please login.'
            )

            return redirect('accounts:login')

        context = {
            'form': form,
        }

        return render(request, 'accounts/register.html', context)


#Login view
class LoginView(View):

    def get(self, request):

        if request.user.is_authenticated:
            return redirect('polls:poll_list')

        form = AuthenticationForm(request)

        context = {
            'form': form,
            'next': request.GET.get('next', ''),
        }

        return render(request, 'accounts/login.html', context)

    def post(self, request):

        if request.user.is_authenticated:
            return redirect('polls:poll_list')

        form = AuthenticationForm(
            request,
            data=request.POST
        )

        username = request.POST.get('username', '')

        if throttle.is_locked_out(request, username):
            messages.error(
                request,
                'Too many failed login attempts. Please try again later.'
            )

            context = {
                'form': AuthenticationForm(request),
                'next': request.POST.get('next', ''),
            }

            return render(
                request,
                'accounts/login.html',
                context,
                status=429
            )

        if form.is_valid():

            user = form.get_user()

            throttle.clear_failures(request, username)

            login(request, user)

            next_url = request.POST.get('next', '')

            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure()
            ):
                return redirect(next_url)

            return redirect('polls:poll_list')

        throttle.record_failure(request, username)

        context = {
            'form': form,
            'next': request.POST.get('next', ''),
        }

        return render(request, 'accounts/login.html', context)


#Logout view
class LogoutView(View):

    def post(self, request):

        logout(request)

        messages.success(
            request,
            'You have been logged out successfully.'
        )

        return redirect('accounts:login')