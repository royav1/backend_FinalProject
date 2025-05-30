from django.utils.timezone import make_aware
from datetime import datetime
from django.utils.timezone import now

# Each sale event has a name, start, and end date
sale_events = [
    {
        "name": "New Year’s Sale",
        "start": make_aware(datetime(2025, 1, 1)),
        "end": make_aware(datetime(2025, 1, 7)),
    },
    {
        "name": "Valentine’s Day Sale",
        "start": make_aware(datetime(2025, 2, 1)),
        "end": make_aware(datetime(2025, 2, 14)),
    },
    {
        "name": "Spring Event Part 1",
        "start": make_aware(datetime(2025, 3, 20)),
        "end": make_aware(datetime(2025, 4, 25)),
    },
    {
        "name": "Spring Event Part 2",
        "start": make_aware(datetime(2025, 4, 1)),
        "end": make_aware(datetime(2025, 4, 7)),
    },
    {
        "name": "Mother’s Day",
        "start": make_aware(datetime(2025, 5, 1)),
        "end": make_aware(datetime(2025, 5, 12)),
    },
    {
        "name": "Summer Sale",
        "start": make_aware(datetime(2025, 6, 15)),
        "end": make_aware(datetime(2025, 6, 25)),
    },
    {
        "name": "Prime Day",
        "start": make_aware(datetime(2025, 7, 18)),
        "end": make_aware(datetime(2025, 7, 23)),
    },
    {
        "name": "Back to School Sale",
        "start": make_aware(datetime(2025, 8, 10)),
        "end": make_aware(datetime(2025, 8, 20)),
    },
    {
        "name": "Early Holiday Deals",
        "start": make_aware(datetime(2025, 10, 20)),
        "end": make_aware(datetime(2025, 10, 30)),
    },
    {
        "name": "Black Friday",
        "start": make_aware(datetime(2025, 11, 28)),
        "end": make_aware(datetime(2025, 11, 28)),
    },
    {
        "name": "Cyber Monday",
        "start": make_aware(datetime(2025, 12, 1)),
        "end": make_aware(datetime(2025, 12, 1)),
    },
    {
        "name": "Holiday Sale",
        "start": make_aware(datetime(2025, 12, 5)),
        "end": make_aware(datetime(2025, 12, 18)),
    },
    {
        "name": "Boxing Day",
        "start": make_aware(datetime(2025, 12, 26)),
        "end": make_aware(datetime(2025, 12, 26)),
    },
    {
        "name": "testing sale event",
        "start": make_aware(datetime(2025, 5, 17)),
        "end": make_aware(datetime(2025, 5, 18)),
    }, 
    {
        "name": "brand new test event ",
        "start": make_aware(datetime(2025, 5, 20)),
        "end": make_aware(datetime(2025, 5, 21)),
    }
]

def get_current_sale_event():
    today = now().date()
    for event in sale_events:
        if event["start"].date() <= today <= event["end"].date():
            return event["name"]
    return None