from django.contrib import admin
from django.db.models import Count, Avg, Sum
from django.utils.html import format_html
from django.urls import reverse
from nutrition.models import GroceryList, UserIngredient


@admin.register(GroceryList)
class GroceryListAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'get_item_count', 'get_total_items')
    list_filter = ('created_at',)
    search_fields = ('user__username',)
    readonly_fields = ('created_at',)

    def get_item_count(self, obj):
        return len(obj.items) if obj.items else 0
    get_item_count.short_description = 'Categories'

    def get_total_items(self, obj):
        if obj.items:
            return sum(len(category_items) for category_items in obj.items.values())
        return 0
    get_total_items.short_description = 'Total Items'


@admin.register(UserIngredient)
class UserIngredientAdmin(admin.ModelAdmin):
    list_display = ('user', 'ingredient', 'quantity', 'unit', 'created_at', 'updated_at')
    list_filter = ('ingredient__category', 'unit', 'created_at')
    search_fields = ('user__username', 'ingredient__name')
    autocomplete_fields = ['user', 'ingredient']


# Custom admin views for analytics
class SystemAnalyticsAdmin(admin.ModelAdmin):
    change_list_template = 'admin/system_analytics_change_list.html'

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context)

        # User statistics
        from django.contrib.auth.models import User
        from accounts.models import UserProfile
        from nutrition.models import MealHistory

        user_stats = {
            'total_users': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'profiles_completed': UserProfile.objects.exclude(age__isnull=True).count(),
        }

        # Meal history statistics
        meal_stats = MealHistory.objects.aggregate(
            total_meals=Count('id'),
            avg_rating=Avg('rating'),
        )

        # Popular foods
        popular_foods = MealHistory.objects.values('food__name').annotate(
            count=Count('id')
        ).order_by('-count')[:10]

        # System usage by month
        from django.db.models.functions import TruncMonth
        usage_stats = MealHistory.objects.annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')

        # Feedback statistics
        feedback_stats = FoodFeedback.objects.aggregate(
            total_feedback=Count('id'),
            avg_score=Avg('score'),
        )

        response.context_data.update({
            'user_stats': user_stats,
            'meal_stats': meal_stats,
            'popular_foods': popular_foods,
            'usage_stats': usage_stats,
            'feedback_stats': feedback_stats,
        })

        return response


class PopularMealsAdmin(admin.ModelAdmin):
    change_list_template = 'admin/popular_meals_change_list.html'

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context)

        from nutrition.models import MealHistory, Food

        # Most recommended foods
        popular_foods = MealHistory.objects.values(
            'food__name', 'food__category', 'food__diet_type'
        ).annotate(
            recommendation_count=Count('id'),
            avg_rating=Avg('rating')
        ).order_by('-recommendation_count')[:20]

        # Foods by category
        category_popularity = MealHistory.objects.values('food__category').annotate(
            count=Count('id')
        ).order_by('-count')

        # Foods by diet type
        diet_popularity = MealHistory.objects.values('food__diet_type').annotate(
            count=Count('id')
        ).order_by('-count')

        # User feedback analysis
        feedback_analysis = FoodFeedback.objects.values('score').annotate(
            count=Count('id')
        ).order_by('score')

        response.context_data.update({
            'popular_foods': popular_foods,
            'category_popularity': category_popularity,
            'diet_popularity': diet_popularity,
            'feedback_analysis': feedback_analysis,
        })

        return response


# Register the analytics views
# Note: ML model classes are not registered as they don't have admin interfaces
