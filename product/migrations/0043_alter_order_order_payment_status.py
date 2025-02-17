# Generated by Django 3.2.23 on 2024-04-15 12:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0042_order_notifications_statuses'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='order_payment_status',
            field=models.CharField(blank=True, choices=[('success', 'success'), ('failed', 'failed'), ('pending', 'pending'), ('pending-refund', 'pending-refund'), ('awaiting-refund-action', 'awaiting-refund-action'), ('partially-refunded', 'partially-refunded'), ('refunded', 'refunded'), ('partially-failed-refund', 'partially-failed-refund'), ('failed-refund', 'failed-refund')], editable=False, max_length=25, null=True),
        ),
    ]
