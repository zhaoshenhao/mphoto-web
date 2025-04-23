import logging
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils.timezone import now
from .forms import UserUpdateForm
from .utils.tools import get_all_events

logger = logging.getLogger(__name__)


def home_view(request):
    events = get_all_events(request)
    print(events)
    return render(request, 'web_admin/home.html', {
            'events': events,
            'page_title': 'MPhoto Search'
        })

def user_login(request):
    if request.method == 'POST':
        email = request.POST['username']  # Using email as username
        password = request.POST['password']
        user = authenticate(request, email=email, password=password)
        if user is not None:
            login(request, user)
            user.last_login = now()
            user.save(update_fields=['last_login'])

            logger.info(f"User {user.email} authenticated and logged in successfully")
            logger.info(f"Request user: {request.user}, Authenticated: {request.user.is_authenticated}")
            return redirect('dashboard')
        else:
            messages.error(request, 'Authentication failed: Invalid email or password')
            logger.error("Authentication failed")
    return render(request, 'web_admin/login.html')

@login_required
def user_logout(request):
    logout(request)
    return redirect('login')

@login_required
def dashboard(request):
    logger.info(f"Dashboard accessed by {request.user}, Authenticated: {request.user.is_authenticated}")
    return render(request, 'web_admin/dashboard.html', {'is_db': "no"})

@login_required
def update_profile(request):
    user = request.user
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=user, for_admin=False)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully')
        else:
            messages.error(request, 'Failed to update profile. Please check your input.')
    else:
        form = UserUpdateForm(
            instance=user,
            for_admin=False,
            initial={
                'created_timestamp': user.created_timestamp,
                'updated_timestamp': user.updated_timestamp,
            }
        )
    return render(request, 'web_admin/profile.html', {
        'form': form,
        'page_title': "My Profile",
    })

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Password changed successfully')
            return redirect('dashboard')
        else:
            messages.error(request, 'Password change failed. Please check your input.')
    else:
        form = PasswordChangeForm(user=request.user)
    return render(request, 'web_admin/password.html', 
                  {'form': form,
                   'page_title': f'Change Password'})


