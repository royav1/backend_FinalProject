# misc_views.py

from rest_framework.response import Response
from rest_framework.decorators import api_view


@api_view(['GET'])
def index(request):
    """
    Simple index view to verify that the backend is reachable.
    """
    return Response('hello')
