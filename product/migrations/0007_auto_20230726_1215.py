# Generated by Django 3.2.18 on 2023-07-26 11:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0006_order_linked_items'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='updated_on',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='order',
            name='order_payment_status',
            field=models.CharField(blank=True, choices=[('failed', 'failed'), ('success', 'success'), ('pending', 'pending')], editable=False, max_length=20, null=True),
        ),
    ]
