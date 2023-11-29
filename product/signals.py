import io
from PIL import Image
from pathlib import Path
import blurhash
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.dispatch import receiver
from django.db.models.signals import pre_save, pre_delete

from trayapp.utils import (
    delete_dir,
    image_resized,
    image_exists,
)
from .models import ItemImage

@receiver(pre_save, sender=ItemImage, dispatch_uid="ItemImage.save_image")
def save_image(sender, instance, **kwargs):
    # add Itemimage (original)
    if instance._state.adding:
        #  item_image
        file, name, content_type, size = image_resized(instance.item_image, 1024, 1024)
        new_item_image = InMemoryUploadedFile(
            file, "ImageField", name, content_type, size, None
        )
        instance.item_image = new_item_image
        instance.item_image_hash = blurhash.encode(
            new_item_image, x_components=4, y_components=3
        )

    # update Itemimage (original)
    if not instance._state.adding:
        # we have 2 cases:
        # - replace old with new
        # - delete old (when 'clear' checkbox is checked)

        #  item_image
        old = sender.objects.get(pk=instance.pk).item_image
        can_delete = image_exists(old.name)
        new = instance.item_image
        if can_delete and ((old and not new) or (old and new and old.url != new.url)):
            old.delete(save=False)
            if image_exists(old.name):
                delete_dir(
                    old.url.replace(old.name, "")
                    .replace(old.format, "")
                    .replace(".", "")
                )
            file, name, content_type, size = image_resized(
                instance.item_image, 1024, 1024
            )
            new_item_image = InMemoryUploadedFile(
                file, "ImageField", name, content_type, size, None
            )
            instance.item_image = new_item_image
            instance.item_image_hash = blurhash.encode(
                new_item_image, x_components=4, y_components=3
            )


@receiver(pre_delete, sender=ItemImage, dispatch_uid="ItemImage.delete_image")
def delete_image(sender, instance, **kwargs):
    try:
        s = sender.objects.get(pk=instance.pk)
        can_delete = image_exists(s.item_image.name)
        if can_delete:
            if (not s.item_image or s.item_image is not None):
                s.item_image.delete(False)
    except sender.DoesNotExist:
        pass
