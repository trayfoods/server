# Generated by Django 3.2.18 on 2023-08-01 00:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_alter_profile_image'),
        ('product', '0005_alter_itemimage_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='linked_stores',
            field=models.ManyToManyField(editable=False, to='users.Store'),
        ),
    ]
