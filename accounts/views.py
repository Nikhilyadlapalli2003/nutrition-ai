from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import UserProfile, UserFeedback
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

def register_view(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect('register')

        user = User.objects.create_user(username=username, password=password)
        login(request, user)
        return redirect('profile')

    return render(request, 'register.html')


def login_view(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid credentials")

    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def profile_view(request):

    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        # keep submitted values on the profile object so the form can re-render them
        profile.age = request.POST.get('age')
        profile.gender = request.POST.get('gender')
        profile.height = request.POST.get('height')
        profile.weight = request.POST.get('weight')
        profile.activity_level = request.POST.get('activity_level')
        profile.health_condition = request.POST.get('health_condition')
        profile.dietary_preference = request.POST.get('dietary_preference')
        profile.goal = request.POST.get('goal')

        # --- validate inputs ---
        errors = False

        # age: integer 10-100
        age_val = request.POST.get('age')
        try:
            age_val = int(age_val)
            if age_val < 10 or age_val > 100:
                errors = True
        except Exception:
            errors = True

        # height: float 100-220 cm
        height_val = request.POST.get('height')
        try:
            height_val = float(height_val)
            if height_val < 100 or height_val > 220:
                errors = True
        except Exception:
            errors = True

        # weight: float 30-200 kg
        weight_val = request.POST.get('weight')
        try:
            weight_val = float(weight_val)
            if weight_val < 30 or weight_val > 200:
                errors = True
        except Exception:
            errors = True

        # required selects / fields
        gender_val = request.POST.get('gender')
        activity_val = request.POST.get('activity_level')
        dietary_val = request.POST.get('dietary_preference')
        goal_val = request.POST.get('goal')
        health_val = request.POST.get('health_condition')

        if not gender_val or not activity_val or not dietary_val or not goal_val or not health_val:
            errors = True

        if errors:
            messages.error(request, "Enter Correctly")
        else:
            profile.age = age_val
            profile.gender = gender_val
            profile.height = height_val
            profile.weight = weight_val
            profile.activity_level = activity_val
            profile.health_condition = health_val
            # ensure the medical_conditions field is also updated for consistency
            profile.medical_conditions = health_val
            profile.dietary_preference = dietary_val
            profile.goal = goal_val
            profile.save()
            
            # Clear today's meal plan so it gets regenerated with the new preferences
            from nutrition.models import MealHistory
            from datetime import date
            MealHistory.objects.filter(user=request.user, date=date.today()).delete()
            
            messages.success(request, "Profile saved successfully!")

    # provide condition choices for the health condition dropdown
    return render(request, 'profile.html', {
        'profile': profile,
        'condition_choices': UserProfile.MEDICAL_CONDITIONS_CHOICES,
    })

@csrf_exempt
@login_required
def submit_feedback(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            message = data.get('message', '').strip()
            if not message:
                return JsonResponse({'success': False, 'error': 'Message cannot be empty'}, status=400)
            
            UserFeedback.objects.create(user=request.user, message=message)
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)