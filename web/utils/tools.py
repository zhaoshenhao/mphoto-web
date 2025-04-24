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

def human_file_size(num, si=False, dp=1):
    thresh = 1000 if si else 1024
    if abs(num) < thresh:
        return f"{num} B"
    units = ["kB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"] if si else \
            ["KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB"]
    u = -1
    r = 10 ** dp
    while abs(num) >= thresh and u < len(units) - 1:
        num /= thresh
        u += 1
    return f"{num:.{dp}f} {units[u]}"

def format_big_integer(n):
    return "{:,}".format(n)

