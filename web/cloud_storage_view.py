from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import CloudStorage
from .forms import CloudStorageForm
from .utils.tools import get_events, get_dt_params
from .utils.auth import user_has_event_permission

@login_required
def cloud_storage(request):
    events = get_events(request)
    return render(request, 'web_admin/cloud_storage.html', {
        'events': events,
        'page_title': 'Cloud Storage'
    })

@login_required
def create_or_edit_cloud_storage(request, cloud_storage_id=None):
    instance = CloudStorage.objects.get(id=cloud_storage_id) if cloud_storage_id else None
    user_has_event_permission(request.user, instance)
    if request.method == 'POST':
        form = CloudStorageForm(request.POST, instance=instance, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cloud storage saved successfully.')
            return redirect('cloud_storage')
    else:
        form = CloudStorageForm(instance=instance, user=request.user)
    return render(request, 'web_admin/cloud_storage_form.html', {
        'form': form,
        'page_title': f"Edit Cloud Storage" if cloud_storage_id else "Add Cloud Storage",
        'button_name': 'Update' if cloud_storage_id else "Create"
    })

@login_required
@require_POST
@csrf_exempt
def cloud_storage_data(request):
    draw, start, length, search_value, order = get_dt_params(request)
    event_id = request.POST.get("event_id")

    queryset = CloudStorage.objects.select_related('event')

    if request.user.role != 'admin':
        queryset = queryset.filter(event__eventmanager__user=request.user)

    if event_id:
        queryset = queryset.filter(event_id=event_id)

    if search_value:
        queryset = queryset.filter(
            Q(url__icontains=search_value) |
            Q(description__icontains=search_value) |
            Q(event__name__icontains=search_value)
        )

    total_records = queryset.count()
    queryset = queryset.order_by(order)[start:start+length]

    data = [{
        "event_id": c.event_id,
        "event__name": c.event.name,
        "id": c.id,
        "url": c.url,
        "recursive": c.recursive,
        "description": c.description,
    } for c in queryset]

    return JsonResponse({
        "draw": draw,
        "recordsTotal": total_records,
        "recordsFiltered": total_records,
        "data": data
    })

@login_required
@require_POST
def delete_cloud_storage(request, cloud_storage_id):
    cs = get_object_or_404(CloudStorage, id=cloud_storage_id)
    user_has_event_permission(request.user, cs)
    cs.delete()
    messages.success(request, "Cloud Storage deleted.")
    return JsonResponse({'success': True})
