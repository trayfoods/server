# Generated by Django 3.2.23 on 2024-01-15 00:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0010_order_extra_delivery_fee'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='stores_status',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
