# Generated by Django 3.2.19 on 2023-11-27 01:07

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0022_alter_order_order_status'),
    ]

    operations = [
        migrations.RenameField(
            model_name='order',
            old_name='created_on',
            new_name='created_at',
        ),
        migrations.RenameField(
            model_name='order',
            old_name='updated_on',
            new_name='updated_at',
        ),
    ]
