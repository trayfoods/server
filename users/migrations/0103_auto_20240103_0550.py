# Generated by Django 3.2.23 on 2024-01-03 04:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0102_auto_20240103_0533'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='student',
            name='floor',
        ),
        migrations.RemoveField(
            model_name='student',
            name='room',
        ),
        migrations.AddField(
            model_name='student',
            name='hostel_fields',
            field=models.JSONField(blank=True, default=list, null=True),
        ),
    ]
