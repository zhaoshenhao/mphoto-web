import random
from django.utils.timezone import now
import logging
import settings
from ..models import Event


def get_events(request):
    if request.user.role == 'admin':
        return Event.objects.all().order_by('name')
    else:
        return Event.objects.filter(eventmanager__user=request.user).order_by('name')

def generate_unique_code(event_id, existing_codes):
    while True:
        code = f"{random.randint(0, 9999999999):010}"
        if code not in existing_codes:
            existing_codes.add(code)
            return code

def get_all_events(request):
    return Event.objects.filter(enabled=True, expiry__gt=now()).order_by('name')

