# Generated by Django 3.2.18 on 2023-07-27 01:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0011_order_order_payment_method'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='order_payment_url',
            field=models.CharField(blank=True, editable=False, max_length=200),
        ),
    ]
