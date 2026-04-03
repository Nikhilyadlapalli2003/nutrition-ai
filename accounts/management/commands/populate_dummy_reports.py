from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import HealthReport, UserProfile
import random
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Populate existing HealthReport records with dummy data'

    def handle(self, *args, **options):
        # dummy data options
        health_conditions = [
            'Healthy', 'Overweight', 'Underweight', 'Diabetic', 'Hypertensive',
            'High Cholesterol', 'Obese', 'Normal', 'Pre-diabetic'
        ]
        goals = ['lose_weight', 'gain_weight', 'maintain', 'build_muscle']
        diet_plans = [
            'Standard', 'Vegetarian Balanced', 'Low Sodium', 'Diabetic Friendly',
            'Keto', 'Mediterranean', 'High Protein', 'Low Carb'
        ]

        reports_updated = 0
        for user in User.objects.all():
            # get or create health report (though they should exist)
            report, created = HealthReport.objects.get_or_create(
                user=user,
                defaults={
                    'weight': 0.0,
                    'health_condition': 'Not specified',
                    'goal': 'maintain',
                    'assigned_diet_plan': 'Standard',
                }
            )

            # populate with dummy data
            try:
                profile = user.userprofile
                # use profile data if available
                report.weight = profile.weight or random.uniform(50, 100)
                report.health_condition = profile.health_condition or random.choice(health_conditions)
                report.goal = profile.goal or random.choice(goals)
            except UserProfile.DoesNotExist:
                # fallback to random
                report.weight = random.uniform(50, 100)
                report.health_condition = random.choice(health_conditions)
                report.goal = random.choice(goals)

            report.assigned_diet_plan = random.choice(diet_plans)
            report.final_weight = report.weight + random.uniform(-10, 10) if random.random() > 0.5 else None
            report.goal_achieved = random.random() > 0.7  # 30% chance achieved
            report.created_at = datetime.now() - timedelta(days=random.randint(0, 365))

            report.save()
            reports_updated += 1

        self.stdout.write(
            self.style.SUCCESS(f'Successfully updated {reports_updated} health reports with dummy data')
        )