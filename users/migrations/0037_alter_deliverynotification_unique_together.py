# Generated by Django 3.2.23 on 2024-04-27 07:42

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0044_remove_order_notifications_statuses'),
        ('users', '0036_remove_deliveryperson_is_on_delivery'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='deliverynotification',
            unique_together={('order', 'delivery_person')},
        ),
    ]
