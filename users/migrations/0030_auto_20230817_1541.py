# Generated by Django 3.2.18 on 2023-08-17 14:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0029_auto_20230817_1129'),
    ]

    operations = [
        migrations.AlterField(
            model_name='store',
            name='store_categories',
            field=models.JSONField(blank=True, default=list, null=True),
        ),
        migrations.AlterField(
            model_name='store',
            name='store_phone_numbers',
            field=models.JSONField(blank=True, default=list, null=True),
        ),
    ]
