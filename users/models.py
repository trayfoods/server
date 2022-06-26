from django.db import models
# from django.contrib.gis.db import models
from django.contrib.auth.models import User
from django.dispatch import receiver

from django.db.models.signals import post_save

HOSTEL_LISTS = (("ABOVE_ONLY", "ABOVE_ONLY"),
                ("BALM_OF_GELLIED", "BALM_OF_GELLIED"),
                ("GRACE", "GRACE"), ("CHAMPTIONS", "CHAMPTIONS"), ("SPLENDOR", "SPLENDOR"), ("HOPE", "HOPE"), ("LOVE", "LOVE"))
GENDER_LISTS = (("Male", "Male"), ("Female", "Female"))


class Store(models.Model):
    store_name = models.CharField(max_length=20)
    store_nickname = models.CharField(max_length=20, null=True, blank=True)
    store_category = models.CharField(max_length=15)
    store_rank = models.FloatField(default=0)
    store_products = models.ManyToManyField(
        "product.Item", related_name="store_items", blank=True)
    # store_location = models.PointField(null=True) # Spatial Field Types

    def __str__(self):
        return f"{self.store_name}"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to="images/profile-images/", null=True)
    phone_number = models.CharField(max_length=16)
    gender = models.CharField(max_length=10, choices=GENDER_LISTS)
    is_student = models.BooleanField(default=False)
    # location = models.PointField(null=True) # Spatial Field Types


class Vendor(models.Model):
    user = models.OneToOneField(Profile, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, null=True)


class Client(models.Model):
    user = models.OneToOneField(Profile, on_delete=models.CASCADE)
    hostel = models.CharField(max_length=16, choices=HOSTEL_LISTS)
    room = models.CharField(max_length=20)


class Deliverer(models.Model):
    user = models.OneToOneField(Profile, on_delete=models.CASCADE)
    is_verified = models.BooleanField(default=False)


@receiver(post_save, sender=User)
def update_profile_signal(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    instance.profile.save()
