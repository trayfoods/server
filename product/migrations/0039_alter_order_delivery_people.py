# Generated by Django 3.2.23 on 2023-12-20 06:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0038_auto_20231220_0703'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='delivery_people',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
