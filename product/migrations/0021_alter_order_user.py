# Generated by Django 3.2.19 on 2023-11-20 19:49

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0079_alter_transaction_order'),
        ('product', '0020_alter_order_order_track_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.profile'),
        ),
    ]
