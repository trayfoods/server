# Generated by Django 3.2.23 on 2024-10-20 23:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0054_alter_order_order_payment_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='prev_order_track_id',
            field=models.CharField(editable=False, max_length=24, null=True, unique=True),
        ),
    ]
