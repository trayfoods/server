# Generated by Django 3.2.18 on 2023-07-01 09:37

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0004_auto_20230629_2307'),
    ]

    operations = [
        migrations.AddField(
            model_name='rating',
            name='new_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
    ]
