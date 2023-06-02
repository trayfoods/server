# Generated by Django 3.2.18 on 2023-06-02 22:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0008_alter_order_order_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='item',
            name='product_share_visibility',
            field=models.CharField(choices=[('private', 'private'), ('public', 'public')], default='public', editable=False, max_length=20),
        ),
    ]
