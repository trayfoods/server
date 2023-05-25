# Generated by Django 3.2.18 on 2023-05-12 20:00

from django.db import migrations, models


def copy_id_to_order_id(apps, schema_editor):
    ProductOrder = apps.get_model("your_app_name", "ProductOrder")
    for obj in ProductOrder.objects.all():
        obj.order_id = obj.id
        obj.save()


class Migration(migrations.Migration):
    dependencies = [
        ("product", "0003_auto_20230508_0336"),
    ]


operations = [
    migrations.AddField(
        model_name="productorder",
        name="order_id",
        field=models.AutoField(primary_key=True, serialize=False),
    ),
    migrations.RunPython(copy_id_to_order_id),
    migrations.RemoveField(
        model_name="productorder",
        name="id",
    ),
    migrations.RenameField(
        model_name="productorder",
        old_name="order_id",
        new_name="id",
    ),
]
