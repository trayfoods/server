from django.db import models
# from django.contrib.gis.db import models
from django.contrib.auth.models import User
from django.dispatch import receiver

from django.db.models.signals import post_save
from trayapp.utils import image_resize


class Gender(models.Model):
    name = models.CharField(
        max_length=20, help_text="NAME SHOULD BE IN UPPERCASE!")
    rank = models.FloatField(default=0)

    def __str__(self) -> str:
        return self.name


class Store(models.Model):
    store_name = models.CharField(max_length=20)
    store_nickname = models.CharField(max_length=20, null=True, blank=True)
    store_category = models.CharField(max_length=15)
    store_rank = models.FloatField(default=0)
    store_products = models.ManyToManyField(
        "product.Item", related_name="store_items", blank=True)
    # store_location = models.PointField(null=True) # Spatial Field Types

    def __str__(self):
        return f"{self.store_nickname}"

    class Meta:
        ordering = ['-store_rank']


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to="images/profile-images/", null=True)
    image_hash = models.CharField(
        'Image Hash', editable=False, max_length=32, null=True, blank=True)
    phone_number = models.CharField(max_length=16)
    gender = models.ForeignKey(Gender, on_delete=models.SET_NULL, null=True)
    is_student = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    # location = models.PointField(null=True) # Spatial Field Types

    def __str__(self) -> str:
        return self.user.username

    def save(self, *args, **kwargs):
        if self.image:
            image_resize(self.image, 260, 260)
        super(Profile, self).save(*args, **kwargs)


class Vendor(models.Model):
    user = models.OneToOneField(Profile, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    account_number = models.CharField(max_length=20, null=True, blank=True)
    account_name = models.CharField(max_length=60, null=True, blank=True)
    bank_code = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.user.user.username


class Hostel(models.Model):
    name = models.CharField(max_length=50)
    short_name = models.CharField(max_length=10, null=True, blank=True)
    gender = models.ForeignKey(Gender, on_delete=models.SET_NULL, null=True)
    is_floor = models.BooleanField(default=False)
    floor_count = models.IntegerField(default=0)

    def __str__(self) -> str:
        return self.name


class Client(models.Model):
    user = models.OneToOneField(Profile, on_delete=models.CASCADE)
    hostel = models.ForeignKey(Hostel, on_delete=models.SET_NULL, null=True)
    room = models.TextField(null=True, blank=True)


class Deliverer(models.Model):
    user = models.OneToOneField(Profile, on_delete=models.CASCADE)


@receiver(post_save, sender=User)
def update_profile_signal(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    instance.profile.save()
