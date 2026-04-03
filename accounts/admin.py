from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.db.models import Count, Avg, Sum, Q
from django.utils.html import format_html, mark_safe
from django.urls import reverse
from django.shortcuts import render
from .models import UserProfile, HealthReport, UserFeedback
from nutrition.models import MealHistory, FoodFeedback
from datetime import datetime, timedelta


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'


class HealthReportInline(admin.TabularInline):
    model = HealthReport
    extra = 0
    readonly_fields = ('weight', 'final_weight', 'health_condition', 'goal', 'goal_achieved', 'assigned_diet_plan', 'created_at')
    ordering = ('-created_at',)
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline, HealthReportInline)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_active', 'date_joined', 'get_profile_completion', 'get_meal_count')
    list_filter = ('is_active', 'is_staff', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')

    def get_profile_completion(self, obj):
        try:
            profile = obj.userprofile
            fields = ['age', 'weight', 'height', 'gender', 'activity_level', 'goal', 'dietary_preference']
            completed = sum(1 for field in fields if getattr(profile, field, None) is not None)
            percentage = int((completed / len(fields)) * 100)
            if percentage == 100:
                return format_html('<span style="color: green;">{}%</span>', percentage)
            elif percentage >= 50:
                return format_html('<span style="color: orange;">{}%</span>', percentage)
            else:
                return format_html('<span style="color: red;">{}%</span>', percentage)
        except UserProfile.DoesNotExist:
            return mark_safe('<span style="color: red;">0% (No Profile)</span>')
    get_profile_completion.short_description = 'Profile %'

    def get_meal_count(self, obj):
        from nutrition.models import MealHistory
        return MealHistory.objects.filter(user=obj).count()
    get_meal_count.short_description = 'Meals Logged'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('userprofile')

    def get_current_weight(self, obj):
        try:
            return f"{obj.userprofile.weight} kg"
        except UserProfile.DoesNotExist:
            return 'N/A'
    get_current_weight.short_description = 'Weight'

    def get_meal_count_today(self, obj):
        today = datetime.now().date()
        return MealHistory.objects.filter(user=obj, date=today).count()
    get_meal_count_today.short_description = 'Meals Today'

    def view_meal_schedule(self, request, user_id):
        """Custom view to show detailed meal schedule for a user"""
        user = User.objects.get(id=user_id)

        # Get date range (last 30 days)
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)

        # Get meal history
        meal_history = MealHistory.objects.filter(
            user=user,
            date__gte=start_date,
            date__lte=end_date
        ).select_related('food').order_by('-date', '-created_at')

        # Calculate daily nutrition summaries
        daily_summaries = {}
        for meal in meal_history:
            date_key = meal.date
            if date_key not in daily_summaries:
                daily_summaries[date_key] = {
                    'meals': [],
                    'total_calories': 0,
                    'total_protein': 0,
                    'total_carbs': 0,
                    'total_fats': 0,
                    'meal_count': 0
                }

            daily_summaries[date_key]['meals'].append(meal)
            daily_summaries[date_key]['total_calories'] += meal.calories
            daily_summaries[date_key]['total_protein'] += meal.protein
            daily_summaries[date_key]['total_carbs'] += meal.carbs
            daily_summaries[date_key]['total_fats'] += meal.fats
            daily_summaries[date_key]['meal_count'] += 1

        # Get feedback stats
        feedback_stats = FoodFeedback.objects.filter(user=user).aggregate(
            total_feedback=Count('id'),
            positive_feedback=Count('id', filter=Q(score__gt=0)),
            negative_feedback=Count('id', filter=Q(score__lt=0))
        )

        # ensure there's at least one health report for this user (creates placeholder if needed)
        latest_report = HealthReport.objects.filter(user=user).order_by('-created_at').first()
        if not latest_report:
            latest_report = HealthReport.objects.create(
                user=user,
                weight=0.0,
                health_condition='Not specified',
                goal='maintain',
                assigned_diet_plan='Standard'
            )
        diet_plan = latest_report.assigned_diet_plan if latest_report else 'N/A'

        # prepare trend arrays for charting
        dates = []
        calories = []
        protein = []
        carbs = []
        fats = []
        for d in sorted(daily_summaries.keys()):
            dates.append(d.strftime('%Y-%m-%d'))
            summary = daily_summaries[d]
            calories.append(summary['total_calories'])
            protein.append(summary['total_protein'])
            carbs.append(summary['total_carbs'])
            fats.append(summary['total_fats'])

        context = {
            'user': user,
            'meal_history': meal_history,
            'daily_summaries': daily_summaries,
            'start_date': start_date,
            'end_date': end_date,
            'feedback_stats': feedback_stats,
            'diet_plan': diet_plan,
            'trend_dates': dates,
            'trend_calories': calories,
            'trend_protein': protein,
            'trend_carbs': carbs,
            'trend_fats': fats,
            'title': f'Meal Schedule for {user.username}'
        }

        return self.admin_site.admin_view(self.meal_schedule_view)(request, context)

    def meal_schedule_view(self, request, context):
        """Render the meal schedule template"""
        return render(request, 'admin/user_meal_schedule.html', context)

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('<int:user_id>/meal-schedule/', self.view_meal_schedule, name='user_meal_schedule'),
        ]
        return custom_urls + urls

    def meal_schedule_link(self, obj):
        url = reverse('admin:user_meal_schedule', args=[obj.id])
        return format_html('<a href="{}" target="_blank">📅 View Meal Schedule</a>', url)
    meal_schedule_link.short_description = 'Meal Schedule'

    list_display = ('username', 'email', 'first_name', 'last_name', 'is_active', 'date_joined', 'get_profile_completion', 'get_current_weight', 'get_meal_count_today', 'meal_schedule_link')

    def weekly_days_followed(self, obj):
        report = obj.weekly_report()
        return report['days_followed']
    weekly_days_followed.short_description = 'Weekly Days Followed'

    def monthly_total_adherence(self, obj):
        report = obj.monthly_report()
        return report['total_adherence']
    monthly_total_adherence.short_description = 'Monthly Adherence'

    def weekly_report_display(self, obj):
        report = obj.weekly_report()
        return format_html(
            "<strong>Weekly Report:</strong><br>"
            "Days Followed: {}<br>"
            "Weight Progress: {}<br>"
            "Consistency: {}%",
            report['days_followed'],
            report['weight_progress'],
            report['consistency_percentage']
        )
    weekly_report_display.short_description = 'Weekly Report'

    def monthly_report_display(self, obj):
        report = obj.monthly_report()
        return format_html(
            "<strong>Monthly Report ({}):</strong><br>"
            "Total Adherence: {}<br>"
            "Weight Change: {}<br>"
            "Consistency Rate: {}%",
            report['month_name'],
            report['total_adherence'],
            report['weight_change'],
            report['overall_consistency_rate']
        )
    monthly_report_display.short_description = 'Monthly Report'


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'age', 'gender', 'goal', 'dietary_preference', 'health_condition', 'get_bmi', 'get_meal_count')
    list_filter = ('gender', 'goal', 'dietary_preference', 'activity_level', 'health_condition')
    search_fields = ('user__username', 'user__email')

    def get_bmi(self, obj):
        if obj.weight and obj.height:
            height_m = obj.height / 100
            bmi = obj.weight / (height_m ** 2)
            bmi_formatted = f"{bmi:.1f}"
            if bmi < 18.5:
                return format_html('<span style="color: blue;">{} (Underweight)</span>', bmi_formatted)
            elif bmi < 25:
                return format_html('<span style="color: green;">{} (Normal)</span>', bmi_formatted)
            elif bmi < 30:
                return format_html('<span style="color: orange;">{} (Overweight)</span>', bmi_formatted)
            else:
                return format_html('<span style="color: red;">{} (Obese)</span>', bmi_formatted)
        return 'N/A'
    get_bmi.short_description = 'BMI'

    def get_meal_count(self, obj):
        from nutrition.models import MealHistory
        return MealHistory.objects.filter(user=obj.user).count()
    get_meal_count.short_description = 'Meals'


@admin.register(HealthReport)
class HealthReportAdmin(admin.ModelAdmin):
    list_display = ('user', 'weight', 'final_weight', 'goal', 'goal_status', 'assigned_diet_plan', 'consistency_rate', 'weekly_days_followed', 'monthly_total_adherence', 'meal_schedule_link')
    list_filter = ('goal', 'goal_achieved', 'health_condition', 'assigned_diet_plan')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    readonly_fields = ('created_at', 'weekly_report_display', 'monthly_report_display', 'recent_meals')

    def weight(self, obj):
        return obj.weight
    weight.short_description = 'Starting Weight'

    def final_weight(self, obj):
        return obj.final_weight if obj.final_weight is not None else '—'
    final_weight.short_description = 'Final Weight'

    def goal_status(self, obj):
        return obj.goal_status
    goal_status.short_description = 'Goal Status'

    def consistency_rate(self, obj):
        return f"{obj.consistency_rate}%"
    consistency_rate.short_description = 'Consistency Rate'

    def weekly_days_followed(self, obj):
        report = obj.weekly_report()
        return report['days_followed']
    weekly_days_followed.short_description = 'Weekly Days Followed'

    def meal_schedule_link(self, obj):
        url = reverse('admin:user_meal_schedule', args=[obj.user.id])
        return format_html('<a href="{}" target="_blank">📅 View Meals</a>', url)
    meal_schedule_link.short_description = 'Meals'

    def monthly_total_adherence(self, obj):
        report = obj.monthly_report()
        return report['total_adherence']
    monthly_total_adherence.short_description = 'Monthly Adherence'

    def weekly_report_display(self, obj):
        report = obj.weekly_report()
        return format_html(
            "<strong>Weekly Report:</strong><br>"
            "Days Followed: {}<br>"
            "Weight Progress: {}<br>"
            "Consistency: {}%",
            report['days_followed'],
            report['weight_progress'],
            report['consistency_percentage']
        )
    weekly_report_display.short_description = 'Weekly Report'

    def monthly_report_display(self, obj):
        report = obj.monthly_report()
        return format_html(
            "<strong>Monthly Report ({}):</strong><br>"
            "Total Adherence: {}<br>"
            "Weight Change: {}<br>"
            "Consistency Rate: {}%",
            report['month_name'],
            report['total_adherence'],
            report['weight_change'],
            report['overall_consistency_rate']
        )
    monthly_report_display.short_description = 'Monthly Report'

    def recent_meals(self, obj):
        meals = MealHistory.objects.filter(user=obj.user).select_related('food').order_by('-date', '-created_at')[:20]
        if not meals:
            return "No meals logged"
        lines = []
        for m in meals:
            lines.append(f"{m.date} {m.get_meal_type_display()}: {m.food.description}")
        return format_html("<br>".join(lines))
    recent_meals.short_description = 'Recent Meals (latest 20)'

# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

@admin.register(UserFeedback)
class UserFeedbackAdmin(admin.ModelAdmin):
    list_display = ('user', 'message_preview', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'message')
    readonly_fields = ('created_at',)

    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'


