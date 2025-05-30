# auth_views.py

from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from django.contrib.auth import logout
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from base.models import UserProfile



@api_view(['GET', 'POST'])
def custom_login(request):
    if request.method == 'GET':
        return Response({"message": "Please use POST to log in."})
    view = MyTokenObtainPairView.as_view()
    return view(request._request)


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        return token


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


@api_view(['POST'])
def user_logout(request):
    logout(request)
    access_token = request.headers.get('Authorization')
    if access_token:
        try:
            if access_token.startswith("Bearer "):
                access_token = access_token.split(" ")[1]
            AccessToken(access_token)  # Validate token
        except Exception as e:
            print(f"Error invalidating access token: {e}")
    return Response({"message": "Successfully logged out."}, status=200)

 
@api_view(['GET', 'POST'])
def register(request):
    if request.method == 'GET':
        return Response({"message": "Please use POST to register a new user."})
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    if not username or not email or not password:
        return Response({"error": "All fields (username, email, and password) are required"}, status=400)
    if User.objects.filter(username=username).exists():
        return Response({"error": "Username already exists"}, status=400)
    if User.objects.filter(email=email).exists():
        return Response({"error": "Email already exists"}, status=400)
    user = User.objects.create_user(username=username, email=email, password=password)
    user.is_active = True                                             # required by Django when there is no email activation
    user.is_staff = False                                             # regular users don't have admin cradantials 
    user.save()
    return Response("New user registered successfully")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_info(request):
    user = request.user
    return Response({
        "user_id": user.id,
        "username": user.username,
        "email": user.email
    })

# Returns the current user's global scraping setting (scheduled_scraping_enabled from UserProfile).
# UserProfile- a way to extend Django's User model with extra features in my case, per-user scraping preferences
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_scraping_setting(request):
    """
    Return the scheduled_scraping_enabled value from the user's profile.
    """
    try:
        enabled = request.user.userprofile.scheduled_scraping_enabled
        return Response({"scheduled_scraping_enabled": enabled})
    except Exception as e:
        return Response({"error": str(e)}, status=500)

# Purpose: Ensures every existing user in the DB has a related UserProfile.
# used once to populate existing users that didn't have "UserProfile" that was a later addition
@api_view(['POST'])
def backfill_userprofiles(request):
    created = 0
    for user in User.objects.all():
        profile, was_created = UserProfile.objects.get_or_create(user=user)
        if was_created:
            created += 1
            print(f"✅ Created UserProfile for: {user.username}")
    return Response({"message": f"{created} UserProfile(s) created."})

# Toggles the scheduled_scraping_enabled flag for the current user
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_scraping_setting(request):
    try:
        profile = request.user.userprofile
        profile.scheduled_scraping_enabled = not profile.scheduled_scraping_enabled
        profile.save()
        return Response({
            "scheduled_scraping_enabled": profile.scheduled_scraping_enabled,
            "message": "Scraping setting toggled."
        })
    except UserProfile.DoesNotExist:
        return Response({"error": "User profile not found."}, status=500)


