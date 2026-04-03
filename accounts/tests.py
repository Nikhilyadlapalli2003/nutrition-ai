from django.test import TestCase
from django.contrib.auth.models import User
from .models import HealthReport


class HealthReportTest(TestCase):
    def setUp(self):
        # ensure sample users exist
        users = [
            {'username': 'krishna_sai'},
            {'username': 'venkat'},
            {'username': 'sample_user'},
        ]
        for u in users:
            User.objects.get_or_create(username=u['username'])

    def test_sample_reports_exist(self):
        reports = HealthReport.objects.all()
        self.assertGreaterEqual(reports.count(), 3, "Should have at least three sample health reports")
        usernames = set(r.user.username for r in reports)
        self.assertTrue('krishna_sai' in usernames and 'venkat' in usernames and 'sample_user' in usernames)

    def test_goal_status_and_final_weight(self):
        hr = HealthReport.objects.get(user__username='venkat')
        # venkat is marked as achieved and had a final weight set
        self.assertEqual(hr.goal_status, 'Achieved')
        self.assertIsNotNone(hr.final_weight)

    def test_consistency_rate(self):
        hr = HealthReport.objects.get(user__username='venkat')
        self.assertIsInstance(hr.consistency_rate, float)
        self.assertGreaterEqual(hr.consistency_rate, 0)
        self.assertLessEqual(hr.consistency_rate, 100)

    def test_weekly_report(self):
        hr = HealthReport.objects.get(user__username='venkat')
        report = hr.weekly_report()
        self.assertIn('days_followed', report)
        self.assertIn('weight_progress', report)
        self.assertIn('consistency_percentage', report)

    def test_monthly_report(self):
        hr = HealthReport.objects.get(user__username='venkat')
        report = hr.monthly_report()
        self.assertIn('total_adherence', report)
        self.assertIn('weight_change', report)
        self.assertIn('overall_consistency_rate', report)
