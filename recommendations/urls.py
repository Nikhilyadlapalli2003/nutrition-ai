from django.urls import path
from . import views
from . import knn_views

urlpatterns = [
    path('', views.recommendation_view, name='recommendations'),
    path('feedback/<int:food_id>/<str:action>/', views.feedback_view, name='feedback'),
    
    # Weight logging
    path('log-weight/', views.log_weight_view, name='log_weight'),
    
    # Grocery List
    path('grocery-list/', views.grocery_list_view, name='grocery_list'),
    
    # Ingredient-based recommendations
    path('ingredients/', views.ingredient_recommendations_view, name='ingredient_recommendations'),
    path('manage-ingredients/', views.manage_ingredients_view, name='manage_ingredients'),
    
    # 🤖 KNN-BASED RECOMMENDATIONS
    path('knn/', knn_views.knn_recommendation_view, name='knn_recommendations'),
    path('alternatives/<int:food_id>/', knn_views.get_alternatives_api, name='food_alternatives'),
    path('preferences/', knn_views.preference_analytics_view, name='preferences'),
    path('api/knn-stats/', knn_views.knn_stats_api, name='knn_stats_api'),
    
    # 🤖 MEAL REPLACEMENT
    path('replace/<str:meal_type>/<int:current_food_id>/', knn_views.meal_replacement_view, name='meal_replacement'),
    path('api/replace-meal/', knn_views.replace_meal_api, name='replace_meal_api'),
    
    # 🤖 SVM-BASED HEALTHY RECOMMENDATIONS
    path('svm/', knn_views.svm_healthy_recommendation_view, name='svm_recommendations'),
    path('health/<int:food_id>/', knn_views.meal_health_api, name='meal_health_api'),
    path('healthy-foods/', knn_views.healthy_foods_api, name='healthy_foods_api'),
    path('healthy-foods/<str:meal_type>/', knn_views.healthy_foods_api, name='healthy_foods_by_type'),
    path('api/svm-stats/', knn_views.svm_stats_api, name='svm_stats_api'),
]