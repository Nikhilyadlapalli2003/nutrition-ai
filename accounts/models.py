from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):

    ACTIVITY_CHOICES = [
        ('sedentary', 'Sedentary'),
        ('light', 'Light Exercise'),
        ('moderate', 'Moderate Exercise'),
        ('active', 'Very Active'),
    ]

    DIET_CHOICES = [
        ('veg', 'Vegetarian'),
        ('nonveg', 'Non-Vegetarian'),
        ('vegan', 'Vegan'),
        ('keto', 'Keto'),
    ]

    GOAL_CHOICES = [
        ('loss', 'Weight Loss'),
        ('maintain', 'Maintain Weight'),
        ('gain', 'Muscle Gain'),
    ]

    MEDICAL_CONDITIONS_CHOICES = [
        ('diabetes', 'Diabetes'),
        ('hypertension', 'Hypertension'),
        ('heart_disease', 'Heart Disease'),
        ('obesity', 'Obesity'),
        ('none', 'None'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True)
    height = models.FloatField(null=True, blank=True)
    weight = models.FloatField(null=True, blank=True)
    activity_level = models.CharField(max_length=20, choices=ACTIVITY_CHOICES, null=True, blank=True)
    health_condition = models.CharField(max_length=100, null=True, blank=True)
    medical_conditions = models.CharField(
        max_length=100, 
        choices=MEDICAL_CONDITIONS_CHOICES, 
        default='none',
        help_text="Select primary medical condition for dietary recommendations"
    )
    allergies = models.TextField(
        blank=True,
        default='',
        help_text="Comma-separated list of food allergies (e.g., peanuts, shellfish, dairy)"
    )
    sodium_limit_mg = models.IntegerField(
        default=2300,
        help_text="Daily sodium limit in mg (default: 2300 for adults)"
    )
    sugar_limit_g = models.IntegerField(
        default=50,
        help_text="Daily added sugar limit in grams (default: 50g)"
    )
    dietary_preference = models.CharField(max_length=20, choices=DIET_CHOICES, null=True, blank=True)
    goal = models.CharField(max_length=20, choices=GOAL_CHOICES, default='maintain')

    def __str__(self):
        return self.user.username

    def get_allergies_list(self):
        """Return allergies as a list, normalized to lowercase"""
        if not self.allergies:
            return []
        return [allergy.strip().lower() for allergy in self.allergies.split(',')]
    
    def add_allergy(self, allergy):
        """Add a new allergy to the user's profile"""
        allergies_list = self.get_allergies_list()
        allergy = allergy.strip().lower()
        if allergy not in allergies_list:
            allergies_list.append(allergy)
        self.allergies = ', '.join(allergies_list)
        self.save()
    
    def remove_allergy(self, allergy):
        """Remove an allergy from the user's profile"""
        allergies_list = self.get_allergies_list()
        allergy = allergy.strip().lower()
        if allergy in allergies_list:
            allergies_list.remove(allergy)
        self.allergies = ', '.join(allergies_list)
        self.save()
    
    def has_medical_condition(self):
        """Check if user has a medical condition"""
        return self.medical_conditions and self.medical_conditions != 'none'
    
    def get_medical_condition_display_name(self):
        """Get human-readable medical condition name"""
        return dict(self.MEDICAL_CONDITIONS_CHOICES).get(self.medical_conditions, 'None')


# =====================================================
# WEIGHT LOG MODEL
# =====================================================
class WeightLog(models.Model):
    """
    Tracks user's weight over time for progress monitoring
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='weight_logs')
    weight = models.FloatField(help_text="Weight in kg")
    date = models.DateField(auto_now_add=True)
    notes = models.TextField(blank=True, default='', help_text="Optional notes (e.g., morning, after workout)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'date']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.weight}kg on {self.date}"

    @property
    def goal_status(self):
        """Return human-friendly goal status based on fields."""
        if self.goal_achieved:
            return 'Achieved'
        if self.final_weight is None:
            return 'In Progress'
        return 'Not Achieved'


# =====================================================
# HABIT TRACK MODEL
# =====================================================
class HabitTrack(models.Model):
    """
    Tracks eating habit consistency (meal adherence)
    """
    MEAL_CHOICES = [
        ('breakfast', 'Breakfast'),
        ('lunch', 'Lunch'),
        ('dinner', 'Dinner'),
        ('snack', 'Snack/Hydration'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='habit_tracks')
    date = models.DateField()
    meal_type = models.CharField(max_length=20, choices=MEAL_CHOICES)
    
    # Track completion
    completed = models.BooleanField(default=False, help_text="Did user follow meal plan?")
    adherence_score = models.IntegerField(
        default=0,
        choices=[(i, f"{i}%") for i in range(0, 101, 10)],
        help_text="How closely did user adhere to recommendations (0-100%)"
    )
    
    # Optional notes
    notes = models.TextField(blank=True, default='')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', 'meal_type']
        indexes = [
            models.Index(fields=['user', 'date']),
        ]
        unique_together = ('user', 'date', 'meal_type')
    
    def __str__(self):
        return f"{self.user.username} - {self.meal_type} ({self.date})"

    @property
    def goal_status(self):
        """Return human-friendly goal status based on fields."""
        if self.goal_achieved:
            return 'Achieved'
        if self.final_weight is None:
            return 'In Progress'
        return 'Not Achieved'


@receiver(post_save, sender=User)
def create_user_profile_and_report(sender, instance, created, **kwargs):
    """Ensure every new user has a profile and an initial health report."""
    if created:
        UserProfile.objects.create(user=instance)
        # create a placeholder health report so admins can immediately see the record
        HealthReport.objects.create(
            user=instance,
            weight=0.0,
            health_condition='Not specified',
            goal='maintain',
            assigned_diet_plan='Standard'
        )


# if a user logs in and still has no health report, create one automatically
from django.contrib.auth.signals import user_logged_in

@receiver(user_logged_in)
def ensure_health_report(sender, user, request, **kwargs):
    if not HealthReport.objects.filter(user=user).exists():
        HealthReport.objects.create(
            user=user,
            weight=0.0,
            health_condition='Not specified',
            goal='maintain',
            assigned_diet_plan='Standard'
        )


# =====================================================
# ADMIN REPORTS MODEL
# =====================================================
class HealthReport(models.Model):
    """Snapshot of a user's health profile for admin reporting."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='health_reports')
    weight = models.FloatField(help_text="Starting weight in kg")
    final_weight = models.FloatField(
        null=True,
        blank=True,
        help_text="Weight after following diet plan (if available)"
    )
    health_condition = models.CharField(max_length=100)
    goal = models.CharField(max_length=20, choices=UserProfile.GOAL_CHOICES, default='maintain')
    goal_achieved = models.BooleanField(default=False, help_text="Has the user achieved their goal?")
    assigned_diet_plan = models.CharField(max_length=50, default='Standard', help_text="Assigned diet plan name")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Health Report'
        verbose_name_plural = 'Health Reports'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} report ({self.created_at.date()})"
    @property
    def goal_status(self):
        """Return human-friendly goal status based on fields."""
        if self.goal_achieved:
            return 'Achieved'
        if self.final_weight is None:
            return 'In Progress'
        return 'Not Achieved'

    @property
    def consistency_rate(self):
        """Calculate overall consistency rate from habit tracks."""
        from django.db.models import Avg
        avg_adherence = self.user.habit_tracks.aggregate(avg=Avg('adherence_score'))['avg']
        return float(round(avg_adherence or 0, 1))

    def weekly_report(self):
        """Return weekly report data."""
        from django.utils import timezone
        from datetime import timedelta
        from django.db.models import Count, Avg, Min, Max

        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=7)

        # Days followed: count distinct dates with completed=True
        days_followed = self.user.habit_tracks.filter(
            date__range=(start_date, end_date),
            completed=True
        ).values('date').distinct().count()

        # Weight progress: min and max weight in the week
        weight_logs = self.user.weight_logs.filter(date__range=(start_date, end_date))
        if weight_logs.exists():
            min_weight = weight_logs.aggregate(Min('weight'))['weight__min']
            max_weight = weight_logs.aggregate(Max('weight'))['weight__max']
            weight_progress = f"{min_weight:.1f}kg - {max_weight:.1f}kg"
        else:
            weight_progress = "No data"

        # Consistency percentage: average adherence_score
        avg_consistency = self.user.habit_tracks.filter(
            date__range=(start_date, end_date)
        ).aggregate(avg=Avg('adherence_score'))['avg'] or 0

        return {
            'days_followed': days_followed,
            'weight_progress': weight_progress,
            'consistency_percentage': round(avg_consistency, 1)
        }

    def monthly_report(self):
        """Return monthly report data."""
        from django.utils import timezone
        from datetime import timedelta
        from django.db.models import Count, Avg, Min, Max

        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)

        # Total adherence: sum of completed meals
        total_adherence = self.user.habit_tracks.filter(
            date__range=(start_date, end_date),
            completed=True
        ).count()

        # Weight change: starting weight - ending weight
        weight_logs = self.user.weight_logs.filter(date__range=(start_date, end_date)).order_by('date')
        if weight_logs.exists():
            start_weight = weight_logs.first().weight
            end_weight = weight_logs.last().weight
            weight_change = f"{start_weight:.1f}kg to {end_weight:.1f}kg ({end_weight - start_weight:+.1f}kg)"
        else:
            weight_change = "No data"

        # Overall consistency rate: average adherence_score
        avg_consistency = self.user.habit_tracks.filter(
            date__range=(start_date, end_date)
        ).aggregate(avg=Avg('adherence_score'))['avg'] or 0

        return {
            'month_name': end_date.strftime('%B %Y'),
            'total_adherence': total_adherence,
            'weight_change': weight_change,
            'overall_consistency_rate': round(avg_consistency, 1)
        }

# =====================================================
# USER FEEDBACK MODEL
# =====================================================
class UserFeedback(models.Model):
    """Stores user feedback submitted via the Avatar widget."""
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='avatar_feedbacks')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'User Feedbacks'

    def __str__(self):
        return f"Feedback from {self.user.username if self.user else 'Anonymous'} on {self.created_at.date()}"
