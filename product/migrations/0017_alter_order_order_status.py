# Generated by Django 3.2.23 on 2024-01-24 15:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0016_auto_20240120_0318'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='order_status',
            field=models.CharField(choices=[('not-started', 'not-started'), ('processing', 'processing'), ('partially-accepted', 'partially-accepted'), ('accepted', 'accepted'), ('partially-ready-for-pickup', 'partially-ready-for-pickup'), ('ready-for-pickup', 'ready-for-pickup'), ('partially-out-for-delivery', 'partially-out-for-delivery'), ('out-for-delivery', 'out-for-delivery'), ('partially-delivered', 'partially-delivered'), ('delivered', 'delivered'), ('partially-cancelled', 'partially-cancelled'), ('cancelled', 'cancelled'), ('failed', 'failed')], db_index=True, default='not-started', max_length=26),
        ),
    ]
