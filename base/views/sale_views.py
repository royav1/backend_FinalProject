# sale_views.py

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from scheduled_tasks.sale_events import sale_events

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_sale_events(request):
    """
    Returns a list of all defined sale event names.
    """
    event_names = sorted(set(event["name"] for event in sale_events))
    return Response(event_names)
