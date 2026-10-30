from django.views import View
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth import logout

from .forms import RegistrationForm
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from django.conf import settings
from django.utils.http import url_has_allowed_host_and_scheme


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

            user = form.save()

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

        if form.is_valid():

            user = form.get_user()

            login(request, user)

            next_url = request.POST.get('next', '')

            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure()
            ):
                return redirect(next_url)

            return redirect('polls:poll_list')

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