# Generated by Django 3.2.23 on 2024-01-19 23:48

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0016_auto_20240118_2020'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='wallet',
            name='unsettled_balance',
        ),
    ]
