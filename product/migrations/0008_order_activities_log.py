# Generated by Django 3.2.23 on 2024-01-14 21:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0007_auto_20240114_2205'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='activities_log',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
