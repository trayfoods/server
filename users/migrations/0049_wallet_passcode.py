# Generated by Django 4.2.5 on 2023-09-13 21:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0048_remove_useraccount_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='wallet',
            name='passcode',
            field=models.CharField(blank=True, editable=False, max_length=128, null=True, verbose_name='passcode'),
        ),
    ]
