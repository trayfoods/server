# Generated by Django 3.2.19 on 2023-11-13 23:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0064_remove_profile_is_info_completed'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='is_info_completed',
            field=models.BooleanField(default=False),
        ),
    ]
