import logging
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import SetPasswordForm
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .forms import UserUpdateForm
from .models import User

logger = logging.getLogger(__name__)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def users(request):
    return render(request, 'web_admin/users.html')

@login_required
@require_POST
@user_passes_test(lambda u: u.is_superuser)
@csrf_exempt
def users_data(request):
    draw = int(request.POST.get("draw", 1))
    start = int(request.POST.get("start", 0))
    length = int(request.POST.get("length", 25))
    search_value = request.POST.get("search[value]", "").strip()
    queryset = User.objects.all()
    if search_value:
        queryset = queryset.filter(
            Q(email__icontains=search_value) |
            Q(name__icontains=search_value) |
            Q(phone__icontains=search_value) |
            Q(role__icontains=search_value) |
            Q(enabled__icontains=search_value) |
            Q(description__icontains=search_value)
        )
    total_filtered = queryset.count()
    order_column_index = request.POST.get("order[0][column]")
    order_column_dir = request.POST.get("order[0][dir]", "asc")
    column_map = {
        "0": "id",
        "1": "email",
        "2": "name",
        "3": "phone",
        "4": "description",
        "5": "role",
        "6": "enabled",
        "7": "last_login",
        "8": "updated_timestamp",
        "9": "created_timestamp",
        "10": "api_key"
    }
    order_column = column_map.get(order_column_index, "id")
    if order_column_dir == "desc":
        order_column = f"-{order_column}"
    queryset = queryset.order_by(order_column)[start:start + length]
    data = [{
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "phone": user.phone,
        "description": user.description,
        "role": user.role,
        "enabled": user.enabled,
        "last_login": user.last_login.strftime("%Y-%m-%d %H:%M:%S") if user.last_login else "",
        "created_timestamp": user.created_timestamp.strftime("%Y-%m-%d %H:%M:%S") if user.created_timestamp else "",
        "updated_timestamp": user.updated_timestamp.strftime("%Y-%m-%d %H:%M:%S") if user.updated_timestamp else "",
        'api_key': user.api_key
    } for user in queryset]
    return JsonResponse({
        "draw": draw,
        "recordsTotal": User.objects.count(),
        "recordsFiltered": total_filtered,
        "data": data,
    })

@login_required
@user_passes_test(lambda u: u.is_superuser)
def edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=user, for_admin=True)
        if form.is_valid():
            form.save()
            messages.success(request, 'User updated successfully.')
            return redirect('users')
        else:
            messages.error(request, 'Failed to update the user. Please try again.')
    else:
        form = UserUpdateForm(
            instance=user,
            for_admin=True,
            initial={
                'created_timestamp': user.created_timestamp,
                'updated_timestamp': user.updated_timestamp,
            }
        )
    return render(request, 'web_admin/user_form.html', {
        'form': form,
        'page_title': f"Edit User: {user.email}",
        'button_name': f"Update",
    })

@login_required
@user_passes_test(lambda u: u.is_superuser)
def add_user(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, for_admin=True)
        if form.is_valid():
            new_user = form.save(commit=False)
            new_user.save()
            messages.success(request, 'User created successfully.')
            return redirect('users')  # Redirect back to the users list page
        else:
            messages.error(request, 'Failed to create the user. Please try again.')
    else:
        form = UserUpdateForm(for_admin=True)

    return render(request, 'web_admin/user_form.html', {
        'form': form,
        'page_title': "Add User",
        'button_name': f"Create",
    })

@login_required
@require_POST
@user_passes_test(lambda u: u.is_superuser)
def delete_user(request, user_id):
    try:
        user = get_object_or_404(User, id=user_id)
        user.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def change_password(request, user_id):
    target_user = get_object_or_404(User, pk=user_id)

    if request.method == 'POST':
        form = SetPasswordForm(user=target_user, data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f"Password updated for {target_user.email}")
            return redirect('users')  # or wherever your admin list is
        else:
            messages.error(request, "Password update failed.")
    else:
        form = SetPasswordForm(user=target_user)

    return render(request, 'web_admin/password.html', {
        'form': form,
        'page_title': f'Change Password: {target_user.email}'
    })