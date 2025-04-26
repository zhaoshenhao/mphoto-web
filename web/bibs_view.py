import logging
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import Bib, Event
from .utils.auth import user_has_event_permission
from .utils.tools import get_events, generate_unique_code, get_dt_params
from .forms import BibForm
from datetime import timedelta, date

logger = logging.getLogger(__name__)

@login_required
def bibs(request):
    events = get_events(request)
    return render(request, 'web_admin/bibs.html', {
        'events': events,
        'page_title': 'Bibs'
    })

@login_required
def create_or_edit_bib(request, bib_id=None):
    instance = Bib.objects.get(id=bib_id) if bib_id else None
    user_has_event_permission(request.user, instance)

    if request.method == 'POST':
        form = BibForm(request.POST, instance=instance, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Bib saved successfully.")
            return redirect('bibs')
    else:
        form = BibForm(instance=instance, user=request.user)

    return render(request, 'web_admin/bib_form.html', {
        'form': form,
        'page_title': "Edit Bib" if bib_id else "Add Bib",
        'button_name': "Update" if bib_id else "Create"
    })

@login_required
@require_POST
@csrf_exempt
def bibs_data(request):
    draw, start, length, search_value, order = get_dt_params(request)
    event_id = request.POST.get("event_id")

    queryset = Bib.objects.select_related('event')
    if request.user.role != 'admin':
        queryset = queryset.filter(event__eventmanager__user=request.user)

    if event_id:
        queryset = queryset.filter(event_id=event_id)

    if search_value:
        queryset = queryset.filter(
            Q(bib_number__icontains=search_value) |
            Q(name__icontains=search_value) |
            Q(code__icontains=search_value) |
            Q(enabled__icontains=search_value) |
            Q(event__name__icontains=search_value)
        )
    total_records = queryset.count()
    queryset = queryset.order_by(order)[start:start + length]

    data = [{
        'event_id': p.event.id,
        'event__name': p.event.name,
        'id': p.id,
        'bib_number': p.bib_number,
        'name': p.name,
        'code': p.code,
        'enabled': p.enabled,
        'expiry': p.expiry.strftime('%Y-%m-%d %H:%M:%S')
    } for p in queryset]

    return JsonResponse({
        "draw": draw,
        "recordsTotal": total_records,
        "recordsFiltered": total_records,
        "data": data
    })

@login_required
@require_POST
@user_passes_test(lambda u: u.role == 'admin')
def delete_bib(request, bib_id):
    bib = get_object_or_404(Bib, id=bib_id)
    user_has_event_permission(request.user, bib)
    bib.delete()
    messages.success(request, "Bib deleted.")
    return JsonResponse({'success': True})

@login_required
def import_bib(request):
    if request.method == 'POST':
        event_id = request.POST.get('event_id')  # Retrieve selected event
        expiry_date = request.POST.get('expiry')  # Retrieve expiry date
        event = get_object_or_404(Event, id=event_id)
        user_has_event_permission(request.user, event)
        try:
            expiry_date = date.fromisoformat(expiry_date)
        except ValueError:
            messages.error(request, 'Invalid expiry date format.')
            return redirect('import_bibs')
        use_file = request.POST.get('upload_file_check')
        bib_list = []
        existing_codes = set(Bib.objects.filter(event_id=event_id).values_list('code', flat=True))
        try:
            if use_file:
                upload_file = request.FILES.get('csv_file')
                for line in upload_file.read().decode().splitlines():
                    bib_number, name = line.split(',')
                    code = generate_unique_code(event_id, existing_codes)  # Pass cached codes
                    existing_codes.add(code)
                    bib_list.append(Bib(event_id=event_id, bib_number=bib_number, name=name, code=code, expiry=expiry_date))
            else:
                bib_text = request.POST.get('bib_text')  # Retrieve bib numbers input in text area
                for line in bib_text.splitlines():
                    bib_number, name = line.split(',')
                    code = generate_unique_code(event_id, existing_codes)
                    existing_codes.add(code)
                    bib_list.append(Bib(event_id=event_id, bib_number=bib_number, name=name, code=code, expiry=expiry_date))
            Bib.objects.bulk_create(bib_list, update_conflicts=True,
                                    update_fields=['code', 'expiry'],
                                    unique_fields=['event_id', 'bib_number'])
            messages.success(request, f"{len(bib_list)} Bib numbers successfully imported!")
            return redirect('bibs')
        except Exception as e:
            logger.warning(f"{e}")
            messages.error(request, f"{e}")
    
    default_expiry = now().date() + timedelta(days=365)
    events = get_events(request)
    return render(request, 'web_admin/import_bibs.html', {
        'events': events,
        'default_expiry': default_expiry,
        'page_title': 'Import Bibs',
    })