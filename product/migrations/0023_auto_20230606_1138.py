# Generated by Django 3.2.18 on 2023-06-06 10:38

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('product', '0022_auto_20230606_1138'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='rating',
            name='user_like',
        ),
        migrations.AddField(
            model_name='rating',
            name='user_liked',
            field=models.ManyToManyField(blank=True, editable=False, related_name='user_liked', to=settings.AUTH_USER_MODEL),
        ),
    ]
