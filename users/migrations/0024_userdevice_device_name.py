# Generated by Django 3.2.18 on 2023-08-05 15:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0023_alter_userdevice_device_token'),
    ]

    operations = [
        migrations.AddField(
            model_name='userdevice',
            name='device_name',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
