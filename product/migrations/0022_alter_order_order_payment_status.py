# Generated by Django 3.2.23 on 2024-01-25 06:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0021_alter_order_order_payment_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='order_payment_status',
            field=models.CharField(blank=True, choices=[('failed', 'failed'), ('success', 'success'), ('pending', 'pending'), ('pending-refund', 'pending-refund'), ('partially-refunded', 'partially-refunded'), ('refunded', 'refunded'), ('partially-failed-refund', 'partially-failed-refund'), ('failed-refund', 'failed-refund')], editable=False, max_length=25, null=True),
        ),
    ]
