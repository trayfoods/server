import os
from django.db import models
from django.dispatch import receiver
from django.template.defaultfilters import slugify
from django.utils.translation import gettext_lazy as _
from trayapp.utils import image_resize

PRODUCT_TYPES = (("TYPE", "TYPE"), ("CATEGORY", "CATEGORY"))


def item_directory_path(instance, filename):
    """
    Create a directory path to upload the Product's Image.
    :param object instance:
        The instance where the current file is being attached.
    :param str filename:
        The filename that was originally given to the file.
        This may not be taken into account when determining
        the final destination path.
    :result str: Directory path.file_extension.
    """
    item_name = slugify(instance.product.product_name)
    item_slug = slugify(instance.product.product_slug)
    _, extension = os.path.splitext(filename)
    return f"images/items/{item_slug}/{item_name}{extension}"


class ItemImage(models.Model):
    product = models.ForeignKey("Item", on_delete=models.CASCADE)
    item_image = models.ImageField('Item Image', upload_to=item_directory_path,  # callback function
                                   null=False, blank=False,
                                   help_text=_('Upload Item Image.'))
    item_image_webp = models.ImageField('Webp Item Image',
                                        upload_to=item_directory_path,
                                        null=True, blank=True,
                                        help_text=_('Upload Item Image In Webp Format.'))
    is_primary = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-id']

    def __str__(self) -> str:
        return self.product.product_slug

    # def save(self, *args, **kwargs):
    #     super(ItemImage, self).save(*args, **kwargs)


class Item(models.Model):
    product_name = models.CharField(max_length=200)
    product_qty = models.IntegerField(default=0)
    product_price = models.FloatField()
    product_calories = models.IntegerField(blank=True, null=True)
    product_desc = models.CharField(max_length=500, blank=True, null=True)
    product_category = models.ForeignKey(
        "ItemAttribute", related_name="product_category", on_delete=models.SET_NULL, null=True)
    product_type = models.ForeignKey(
        "ItemAttribute", related_name="product_type", on_delete=models.SET_NULL, null=True)
    product_images = models.ManyToManyField(
        "ItemImage", related_name="product_image", blank=True)
    product_avaliable_in = models.ManyToManyField(
        "users.Store", related_name="avaliable_in_store", blank=True)
    product_creator = models.ForeignKey(
        "users.Vendor", null=True, on_delete=models.SET_NULL, blank=True)
    product_created_on = models.DateTimeField(auto_now_add=True)
    product_clicks = models.IntegerField(default=0)
    product_views = models.IntegerField(default=0)
    product_slug = models.SlugField(null=False, unique=True)

    class Meta:
        ordering = ['-product_clicks']

    def __str__(self):
        return self.product_name

    def save(self, *args, **kwargs):  # auto create product_slug
        if not self.product_slug:
            self.product_slug = slugify(self.product_name)
        return super().save(*args, **kwargs)


class ItemAttribute(models.Model):
    name = models.CharField(max_length=20)
    urlParamName = models.SlugField(null=False, unique=True)
    _type = models.CharField(max_length=20, choices=PRODUCT_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):  # auto create urlParamName
        if not self.urlParamName:
            self.urlParamName = slugify(self.urlParamName)
        return super().save(*args, **kwargs)

# Signals
@receiver(models.signals.post_delete, sender=ItemImage)
def remove_file_from_s3(sender, instance, using, **kwargs):
    instance.item_image.delete(save=False)
