from django.urls import path
from django.contrib import admin
from nutrition.admin import FoodDatabaseAdmin
from nutrition.models import Food
from recommendations.admin import SystemAnalyticsAdmin, PopularMealsAdmin

# Create instances of the admin classes
food_admin = FoodDatabaseAdmin(Food, admin.site)
system_analytics_admin = SystemAnalyticsAdmin(Food, admin.site)  # Using Food as a dummy model
popular_meals_admin = PopularMealsAdmin(Food, admin.site)  # Using Food as a dummy model

urlpatterns = [
    path('analytics/system-analytics/', system_analytics_admin.changelist_view, name='system_analytics'),
    path('analytics/popular-meals/', popular_meals_admin.changelist_view, name='popular_meals'),
]