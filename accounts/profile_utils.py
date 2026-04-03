"""
Utilities for user profile management including dietary restrictions and health conditions.
"""
from .models import UserProfile


def setup_medical_conditions_for_user(user, condition):
    """
    Set medical condition for a user in a friendly way
    
    Args:
        user: User object
        condition: One of 'diabetes', 'hypertension', 'heart_disease', 'none'
    """
    profile = UserProfile.objects.get(user=user)
    valid_conditions = ['diabetes', 'hypertension', 'heart_disease', 'obesity', 'none']
    
    if condition.lower() not in valid_conditions:
        raise ValueError(f"Invalid condition. Must be one of {valid_conditions}")
    
    profile.medical_conditions = condition.lower()
    profile.save()
    return profile


def add_allergies_to_user(user, allergies):
    """
    Add allergies to user profile
    
    Args:
        user: User object
        allergies: String (comma-separated) or List of allergen names
    """
    profile = UserProfile.objects.get(user=user)
    
    if isinstance(allergies, list):
        allergies = ', '.join(allergies)
    
    # Parse and add
    new_allergies = [a.strip().lower() for a in allergies.split(',')]
    existing = profile.get_allergies_list()
    
    for allergy in new_allergies:
        if allergy and allergy not in existing:
            profile.add_allergy(allergy)
    
    return profile


def remove_allergy_from_user(user, allergen):
    """
    Remove a specific allergy from user profile
    
    Args:
        user: User object
        allergen: Allergen name to remove
    """
    profile = UserProfile.objects.get(user=user)
    profile.remove_allergy(allergen)
    return profile


def set_sodium_limit(user, limit_mg=2300):
    """
    Set daily sodium limit for user
    
    Args:
        user: User object
        limit_mg: Daily sodium limit in milligrams (default: 2300)
    """
    profile = UserProfile.objects.get(user=user)
    profile.sodium_limit_mg = limit_mg
    profile.save()
    return profile


def set_sugar_limit(user, limit_g=50):
    """
    Set daily sugar limit for user
    
    Args:
        user: User object
        limit_g: Daily sugar limit in grams (default: 50)
    """
    profile = UserProfile.objects.get(user=user)
    profile.sugar_limit_g = limit_g
    profile.save()
    return profile


def get_user_dietary_profile(user):
    """
    Get complete dietary profile summary for a user
    
    Returns:
        dict with all dietary restrictions and health conditions
    """
    profile = UserProfile.objects.get(user=user)
    
    return {
        'medical_condition': profile.get_medical_condition_display_name() if hasattr(profile, 'get_medical_condition_display_name') else profile.medical_conditions,
        'has_medical_condition': profile.has_medical_condition() if hasattr(profile, 'has_medical_condition') else False,
        'allergies': profile.get_allergies_list() if hasattr(profile, 'get_allergies_list') else [],
        'sodium_limit_mg': profile.sodium_limit_mg,
        'sugar_limit_g': profile.sugar_limit_g,
        'dietary_preference': profile.get_dietary_preference_display() if hasattr(profile, 'get_dietary_preference_display') else profile.dietary_preference,
    }
