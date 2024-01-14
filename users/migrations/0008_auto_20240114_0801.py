# Generated by Django 3.2.23 on 2024-01-14 07:01

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_rename_whatsapp_phone_numbers_store_whatsapp_numbers'),
    ]

    operations = [
        migrations.AlterField(
            model_name='store',
            name='store_categories',
            field=models.JSONField(blank=True, default=list, editable=False),
        ),
        migrations.AlterField(
            model_name='store',
            name='store_nickname',
            field=models.CharField(max_length=50),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='store',
            name='store_type',
            field=models.CharField(max_length=20),
            preserve_default=False,
        ),
    ]
