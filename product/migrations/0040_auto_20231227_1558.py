# Generated by Django 3.2.23 on 2023-12-27 14:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0039_alter_order_delivery_people'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='delivery_person_note',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AlterField(
            model_name='order',
            name='order_status',
            field=models.CharField(choices=[('not-started', 'not-started'), ('processing', 'processing'), ('out-for-delivery', 'out-for-delivery'), ('ready-for-pickup', 'ready-for-pickup'), ('delivered', 'delivered'), ('cancelled', 'cancelled')], db_index=True, default='not-started', max_length=20),
        ),
    ]
