# Generated by Django 3.2.23 on 2024-03-25 15:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0032_alter_order_order_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='vendors_seen',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
