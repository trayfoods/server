from django.db import models
from django.template.defaultfilters import slugify
from django.db.models.signals import post_delete
# from django.urls import reverse

from trayapp.utils import file_cleanup

PRODUCT_TYPES = (("TYPE", "TYPE"), ("CATEGORY", "CATEGORY"))


class ItemImage(models.Model):
    product = models.ForeignKey("Item", on_delete=models.CASCADE)
    item_image = models.ImageField(upload_to="images/items/")
    is_primary = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)


class Item(models.Model):
    product_name = models.CharField(max_length=200)
    product_price = models.IntegerField()
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
        "users.Vendor", null=True, on_delete=models.SET_NULL)
    product_created_on = models.DateTimeField(auto_now_add=True)
    product_clicks = models.IntegerField(default=0)
    product_views = models.IntegerField(default=0)
    product_slug = models.SlugField(null=False, unique=True)

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

    # def get_absolute_url(self):
    #     return reverse("article_detail", kwargs={"slug": self.slug})


post_delete.connect(
    file_cleanup, sender=ItemImage, dispatch_uid="ItemImage.item_image.file_cleanup"
)
