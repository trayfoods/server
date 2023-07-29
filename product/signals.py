import io

from PIL import Image
from pathlib import Path
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.files.images import ImageFile
from django.dispatch import receiver
from django.db.models.signals import pre_save, pre_delete
from trayapp.utils import delete_dir, image_resized
from .models import ItemImage


def _convert_to_webp(f_object: InMemoryUploadedFile):
    suffix = Path(f_object._name).suffix
    if suffix == ".webp":
        return f_object._name, f_object

    new_file_name = str(Path(f_object._name).with_suffix(".webp"))
    image = Image.open(f_object.file)
    thumb_io = io.BytesIO()
    image.save(thumb_io, "webp", optimize=True, quality=95)

    new_f_object = InMemoryUploadedFile(
        thumb_io,
        f_object.field_name,
        new_file_name,
        f_object.content_type,
        f_object.size,
        f_object.charset,
        f_object.content_type_extra,
    )

    return new_file_name, new_f_object


@receiver(pre_save, sender=ItemImage, dispatch_uid="ItemImage.save_image")
def save_image(sender, instance, **kwargs):
    # add Itemimage (original | webp_version)
    if instance._state.adding:
        #  item_image
        file, name, content_type, size = image_resized(instance.item_image, 1024, 1024)
        new_item_image = InMemoryUploadedFile(
            file, "ImageField", name, content_type, size, None
        )
        instance.item_image = new_item_image

        #  item_image_webp
        new_file_name, new_f_object = _convert_to_webp(f_object=new_item_image)
        instance.item_image_webp = ImageFile(new_f_object, new_file_name)

    # update Itemimage (original | webp_version)
    if not instance._state.adding:
        # we have 2 cases:
        # - replace old with new
        # - delete old (when 'clear' checkbox is checked)

        #  item_image
        Wold = sender.objects.get(pk=instance.pk).item_image_webp
        old = sender.objects.get(pk=instance.pk).item_image
        new = instance.item_image
        if (old and not new) or (old and new and old.url != new.url):
            old.delete(save=False)
            Wold.delete(save=False)
            delete_dir(
                old.url.replace(old.name, "").replace(old.format, "").replace(".", "")
            )
            file, name, content_type, size = image_resized(
                instance.item_image, 1024, 1024
            )
            new_item_image = InMemoryUploadedFile(
                file, "ImageField", name, content_type, size, None
            )
            instance.item_image = new_item_image
            new_file_name, new_f_object = _convert_to_webp(f_object=new_item_image)
            instance.item_image_webp = ImageFile(new_f_object, new_file_name)


@receiver(pre_delete, sender=ItemImage, dispatch_uid="ItemImage.delete_image")
def delete_image(sender, instance, **kwargs):
    s = sender.objects.get(pk=instance.pk)

    if (not s.item_image or s.item_image is not None) and (
        not s.item_image_webp or s.item_image_webp is not None
    ):
        s.item_image.delete(False)
        s.item_image_webp.delete(False)
