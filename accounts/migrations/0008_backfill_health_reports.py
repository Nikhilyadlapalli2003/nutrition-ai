from django.db import migrations


def create_reports(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    HealthReport = apps.get_model('accounts', 'HealthReport')

    for user in User.objects.all():
        HealthReport.objects.get_or_create(
            user=user,
            defaults={
                'weight': 0.0,
                'health_condition': 'Not specified',
                'goal': 'maintain',
                'assigned_diet_plan': 'Standard',
            }
        )


def reverse_reports(apps, schema_editor):
    # no-op: we don't want to delete reports on rollback
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_healthreport_assigned_diet_plan'),
    ]

    operations = [
        migrations.RunPython(create_reports, reverse_reports),
    ]
