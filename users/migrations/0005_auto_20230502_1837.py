# Generated by Django 3.2.18 on 2023-05-02 17:37

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_auto_20230501_1829'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='transaction',
            name='amount',
            field=models.FloatField(blank=True, default=0.0, editable=False, null=True),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='user',
            field=models.OneToOneField(editable=False, on_delete=django.db.models.deletion.CASCADE, to='users.profile'),
        ),
        migrations.AlterField(
            model_name='vendor',
            name='balance',
            field=models.FloatField(blank=True, default=0.0, editable=False, null=True),
        ),
    ]
