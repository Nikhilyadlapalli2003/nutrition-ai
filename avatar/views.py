import json
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from accounts.models import UserProfile
from accounts.progress_utils import get_user_progress_summary, get_progress_goals
from nutrition.models import MealHistory
from nutrition.utils import calculate_bmr, calculate_tdee, adjust_calories_by_goal, calculate_macros

@csrf_exempt
def chat_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            message = data.get('message', '').lower().strip()
            
            user_name = request.user.first_name or request.user.username if request.user.is_authenticated else "there"
            
            response_data = {
                'text': f'I am not sure how to help with that yet. Try saying "Hii", or ask about your "diet plan", "progress", "goals", or "meals", {user_name}!',
                'gesture': 'idle'
            }
            
            # Diet Plan
            if 'diet' in message and 'plan' in message:
                if request.user.is_authenticated:
                    try:
                        profile = UserProfile.objects.get(user=request.user)
                        bmr = calculate_bmr(profile)
                        tdee = calculate_tdee(bmr, profile.activity_level)
                        target_calories = adjust_calories_by_goal(tdee, profile.goal)
                        macros = calculate_macros(target_calories)
                        
                        goal_str = "weight loss" if profile.goal == 'loss' else "muscle gain" if profile.goal == 'gain' else "maintenance"
                        
                        response_data['text'] = (
                            f"Based on your profile ({goal_str}), your personalized daily target is "
                            f"**{target_calories} calories**.<br><br>"
                            f"Recommended Macros:<br>"
                            f"• Protein: {macros['protein']}g<br>"
                            f"• Carbs: {macros['carbs']}g<br>"
                            f"• Fats: {macros['fats']}g"
                        )
                        response_data['gesture'] = 'present' # Optional animation
                    except UserProfile.DoesNotExist:
                        response_data['text'] = "I couldn't find your profile data. Please make sure your profile is complete."
                else:
                    response_data['text'] = "Please log in to generate a personalized diet plan."
            
            # Progress
            elif 'progress' in message:
                if request.user.is_authenticated:
                    try:
                        progress = get_user_progress_summary(request.user)
                        weight_change = progress['weight']['weight_change']
                        adherence = progress['calorie_adherence']['adherence_percent']
                        streak = progress['eating_consistency']['consistency_streak']
                        
                        # Handle cases where value is None
                        weight_change_str = f"{weight_change} kg" if weight_change is not None else "Not tracked yet"
                        
                        response_data['text'] = (
                            f"Here's your latest progress:<br>"
                            f"• Weight Change: {weight_change_str}<br>"
                            f"• Calorie Adherence: {adherence}%<br>"
                            f"• Consistency Streak: {streak} days<br><br>"
                            f"Keep up the great work!"
                        )
                        response_data['gesture'] = 'thumbs_up'
                    except Exception as e:
                        response_data['text'] = "I had trouble fetching your progress. Make sure you've logged some data!"
                else:
                    response_data['text'] = "Please log in to check your progress."
            
            # Goals
            elif 'goal' in message:
                if request.user.is_authenticated:
                    try:
                        goals = get_progress_goals(request.user)
                        primary_goal = goals['goal_description']
                        response_data['text'] = f"Your current primary goal is **{primary_goal}**.<br>"
                        
                        if goals['primary_goal'] == 'loss':
                            target = goals['targets']['weight_loss']['target']
                            response_data['text'] += f"Your target weight is {target} kg."
                        elif goals['primary_goal'] == 'gain':
                            target = goals['targets']['muscle_gain']['target']
                            response_data['text'] += f"Your target weight is {target} kg."
                        else:
                            target = goals['targets']['calorie_adherence']['target_calories']
                            response_data['text'] += f"Your daily calorie target is {target} kcal."
                            
                        response_data['gesture'] = 'present'
                    except Exception as e:
                        response_data['text'] = "I had trouble fetching your goals. Do you have a profile set up?"
                else:
                    response_data['text'] = "Please log in to view your goals."
                    
            # Meals / Food
            elif 'meal' in message or 'eat' in message or 'food' in message or 'ate' in message:
                if request.user.is_authenticated:
                    today = datetime.now().date()
                    meals = MealHistory.objects.filter(user=request.user, date=today)
                    if meals.exists():
                        total_cals = sum(m.calories for m in meals)
                        meal_list = ", ".join([m.food.name for m in meals])
                        response_data['text'] = (
                            f"Today you've consumed {total_cals} calories.<br>"
                            f"You ate: {meal_list}."
                        )
                        response_data['gesture'] = 'thumbs_up'
                    else:
                        response_data['text'] = "You haven't logged any meals for today yet."
                else:
                    response_data['text'] = "Please log in to check your meals."
                    
            # Greetings
            elif 'hello' in message or 'hi' in message or 'hey' in message:
                response_data['text'] = f'Hello {user_name}! How can I help you today? You can ask me about your diet plan, progress, goals, or meals.'
                response_data['gesture'] = 'wave'
            
            return JsonResponse(response_data)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)
