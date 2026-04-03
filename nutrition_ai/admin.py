from django.contrib.admin import AdminSite
from django.contrib.admin.apps import AdminConfig


class NutritionAdminSite(AdminSite):
    site_header = "Nutrition AI Administration"
    site_title = "Nutrition AI Admin Portal"
    index_title = "Welcome to Nutrition AI Admin Portal"
    index_template = 'admin/index.html'

    def get_app_list(self, request):
        """
        Return a sorted list of all the installed apps that have been
        registered in this site.
        """
        app_list = super().get_app_list(request)

        # Add custom analytics sections
        analytics_app = {
            'name': 'Analytics',
            'app_label': 'analytics',
            'models': [
                {
                    'name': 'System Analytics',
                    'object_name': 'SystemAnalytics',
                    'admin_url': '/admin/analytics/system-analytics/',
                    'add_url': None,
                    'view_only': True,
                },
                {
                    'name': 'Popular Meals',
                    'object_name': 'PopularMeals',
                    'admin_url': '/admin/analytics/popular-meals/',
                    'add_url': None,
                    'view_only': True,
                },
                {
                    'name': 'Food Database',
                    'object_name': 'FoodDatabase',
                    'admin_url': '/admin/nutrition/food/',
                    'add_url': '/admin/nutrition/food/add/',
                    'view_only': False,
                },
            ],
        }

        # Insert analytics app at the beginning
        app_list.insert(0, analytics_app)

        return app_list

    def index(self, request, extra_context=None):
        """
        Display the main admin index page, which lists all of the installed
        apps that have been registered in this site.
        """
        from django.contrib.auth.models import User
        from nutrition.models import Food

        extra_context = extra_context or {}

        # Add some basic stats to the context
        extra_context.update({
            'user_count': User.objects.count(),
            'food_count': Food.objects.count(),
        })

        return super().index(request, extra_context)


class NutritionAdminConfig(AdminConfig):
    default_site = 'nutrition_ai.admin.NutritionAdminSite'