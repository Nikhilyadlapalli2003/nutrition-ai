from django.contrib import admin
from django.db.models import Count, Avg, Sum
from django.utils.html import format_html
from django.urls import reverse
from .models import Food, Ingredient, FoodIngredient


class FoodIngredientInline(admin.TabularInline):
    model = FoodIngredient
    extra = 1
    autocomplete_fields = ['ingredient']


@admin.register(Food)
class FoodAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'diet_type', 'calories', 'protein', 'carbs', 'fats', 'get_ingredient_count', 'is_popular')
    list_filter = ('category', 'diet_type', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    inlines = [FoodIngredientInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'category', 'diet_type')
        }),
        ('Nutritional Information', {
            'fields': ('calories', 'protein', 'carbs', 'fats', 'fiber', 'sugar'),
            'classes': ('collapse',)
        }),
        ('Portion Information', {
            'fields': ('serving_size', 'serving_unit'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_ingredient_count(self, obj):
        return obj.foodingredient_set.count()
    get_ingredient_count.short_description = 'Ingredients'

    def is_popular(self, obj):
        # Check if food has been recommended frequently
        from nutrition.models import MealHistory
        count = MealHistory.objects.filter(food=obj).count()
        if count > 10:
            return format_html('<span style="color: green;">★ Popular ({})</span>', count)
        elif count > 5:
            return format_html('<span style="color: orange;">● Moderate ({})</span>', count)
        else:
            return format_html('<span style="color: gray;">○ Low ({})</span>', count)
    is_popular.short_description = 'Popularity'


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'get_food_count', 'created_at')
    list_filter = ('category', 'created_at')
    search_fields = ('name',)
    ordering = ('name',)

    def get_food_count(self, obj):
        return obj.foods.count()
    get_food_count.short_description = 'Used in Foods'


@admin.register(FoodIngredient)
class FoodIngredientAdmin(admin.ModelAdmin):
    list_display = ('food', 'ingredient', 'quantity', 'unit')
    list_filter = ('ingredient__category', 'unit')
    search_fields = ('food__name', 'ingredient__name')
    autocomplete_fields = ['food', 'ingredient']


# Custom admin views for statistics
class FoodDatabaseAdmin(admin.ModelAdmin):
    change_list_template = 'admin/food_database_change_list.html'

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context)

        # Calculate statistics
        food_stats = Food.objects.aggregate(
            total_foods=Count('id'),
            avg_calories=Avg('calories'),
            total_protein=Sum('protein'),
        )

        category_stats = Food.objects.values('category').annotate(
            count=Count('id')
        ).order_by('-count')

        diet_stats = Food.objects.values('diet_type').annotate(
            count=Count('id')
        ).order_by('-count')

        ingredient_stats = Ingredient.objects.values('category').annotate(
            count=Count('id')
        ).order_by('-count')

        response.context_data.update({
            'food_stats': food_stats,
            'category_stats': category_stats,
            'diet_stats': diet_stats,
            'ingredient_stats': ingredient_stats,
        })

        return response