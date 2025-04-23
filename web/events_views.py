import logging
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import Event, CloudStorage, Bib, Photo, BibPhoto, FacePhoto, EventManager
from .forms import EventForm
from .utils.auth import user_has_event_permission


logger = logging.getLogger(__name__)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def events(request):
    return render(request, 'web_admin/events.html', {'page_title': 'Events'})

@login_required
def event_list(request):
    return render(request, 'web_admin/event_list.html', {'page_title': 'My Events'})

@require_POST
@csrf_exempt
@login_required
def events_data(request):
    draw = int(request.POST.get("draw", 1))
    start = int(request.POST.get("start", 0))
    length = int(request.POST.get("length", 25))
    search_value = request.POST.get("search[value]", "").strip()

    order_column_idx = request.POST.get("order[0][column]")
    order_column = request.POST.get(f"columns[{order_column_idx}][data]", "id")
    order_dir = request.POST.get("order[0][dir]", "asc")
    order = f"{'' if order_dir == 'asc' else '-'}{order_column}"

    queryset = Event.objects.all()
    if request.user.role != 'admin':
        queryset = queryset.filter(event__eventmanager__user=request.user)

    if search_value:
        queryset = queryset.filter(
            Q(name__icontains=search_value) |
            Q(enabled__icontains=search_value) |
            Q(expiry__icontains=search_value)
            )

    total = queryset.count()
    queryset = queryset.order_by(order)[start:start + length]

    data = [{
        "id": event.id,
        "name": event.name,
        "enabled": event.enabled,
        "expiry": event.expiry.strftime("%Y-%m-%d %H:%M:%S"),
    } for event in queryset]

    return JsonResponse({
        "draw": draw,
        "recordsTotal": total,
        "recordsFiltered": total,
        "data": data,
    })

@login_required
@user_passes_test(lambda u: u.is_superuser)
def add_event(request):
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Event created successfully.')
            return redirect('events')
        else:
            messages.error(request, 'Failed to create event.')
    else:
        form = EventForm()

    return render(request, 'web_admin/event_form.html', {
        'form': form,
        'page_title': 'Add Event',
        'button_name': f"Create",
    })

@login_required
@user_passes_test(lambda u: u.is_superuser)
def edit_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    try:
        current_manager = EventManager.objects.get(event=event)
        current_manager_id = current_manager.user_id
    except EventManager.DoesNotExist:
        current_manager_id = None

    if request.method == 'POST':
        form = EventForm(request.POST, instance=event, current_manager_id=current_manager_id)
        if form.is_valid():
            event = form.save()
            selected_user = form.cleaned_data.get('manager')
            if selected_user:
                if current_manager_id != selected_user.id:
                    # Replace existing manager
                    EventManager.objects.update_or_create(
                        event=event,
                        defaults={'user': selected_user}
                    )
            else:
                # If no manager selected, delete existing
                EventManager.objects.filter(event=event).delete()

            messages.success(request, "Event updated successfully.")
            return redirect('events')
        else:
            messages.error(request, 'Failed to update event.')
    else:
        form = EventForm(instance=event, current_manager_id=current_manager_id)

    return render(request, 'web_admin/event_form.html', {
        'form': form,
        'page_title': f"Edit Event: {event.name}",
        'button_name': "Update"
    })

@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def delete_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    try:
        event.delete()
        messages.success(request, 'Event deleted successfully.')
    except Exception as e:
        messages.error(request, f"Error deleting event: {str(e)}")
    return redirect('events')

@login_required
def view_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    user_has_event_permission(request.user, event)

    cloud_urls = CloudStorage.objects.filter(event=event).values_list('url', flat=True)

    bibs = Bib.objects.filter(event=event)
    bib_total = bibs.count()
    bib_enabled = bibs.filter(enabled=True).count()
    bib_disabled = bib_total - bib_enabled

    photo_stats = Photo.objects.filter(event=event).aggregate(
        total_count=Count('id'),
        total_size=Sum('size')
    )
    bib_photo_count = BibPhoto.objects.filter(event=event).count()
    face_photo_count = FacePhoto.objects.filter(event=event).count()

    context = {
        'event': event,
        'cloud_urls': cloud_urls,
        'bib_total': bib_total,
        'bib_enabled': bib_enabled,
        'bib_disabled': bib_disabled,
        'photo_count': photo_stats['total_count'],
        'photo_total_size': photo_stats['total_size'],
        'bib_photo_count': bib_photo_count,
        'face_photo_count': face_photo_count
    }

    return render(request, 'web_admin/event_view.html', context)