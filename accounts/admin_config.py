"""
Admin interface configuration for UserProfile with medical conditions and allergies.
This file should be integrated into accounts/admin.py or run as a separate setup.
"""

from django.contrib import admin
from .models import UserProfile


class UserProfileAdmin(admin.ModelAdmin):
    list_display = [
        'user', 
        'age', 
        'medical_conditions', 
        'allergies', 
        'dietary_preference',
        'goal'
    ]
    
    list_filter = [
        'medical_conditions',
        'dietary_preference',
        'activity_level',
        'goal'
    ]
    
    search_fields = [
        'user__username',
        'user__email',
        'allergies',
        'health_condition'
    ]
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Physical Profile', {
            'fields': ('age', 'gender', 'height', 'weight')
        }),
        ('Health & Medical', {
            'fields': (
                'medical_conditions',
                'health_condition',
                'sodium_limit_mg',
                'sugar_limit_g'
            ),
            'description': 'Configure medical conditions and nutritional limits'
        }),
        ('Allergies & Restrictions', {
            'fields': ('allergies',),
            'description': 'Enter comma-separated list of allergens (e.g., peanuts, shellfish, dairy)'
        }),
        ('Dietary Preferences', {
            'fields': (
                'dietary_preference',
                'activity_level',
                'goal'
            )
        }),
    )
    
    readonly_fields = ('user',)
    
    def get_readonly_fields(self, request, obj=None):
        if obj is not None:
            # Can't edit user
            return self.readonly_fields
        return []


# Register the admin if not already registered
if not admin.site.is_registered(UserProfile):
    admin.site.register(UserProfile, UserProfileAdmin)
else:
    # Unregister and re-register with new admin class
    admin.site.unregister(UserProfile)
    admin.site.register(UserProfile, UserProfileAdmin)
