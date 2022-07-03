from django.db import models
# from django.contrib.gis.db import models
from django.contrib.auth.models import User
from django.dispatch import receiver

from django.db.models.signals import post_save

# HOSTEL_LISTS = (("ABOVE_ONLY", "ABOVE_ONLY"),
#                 ("BALM_OF_GELLIED", "BALM_OF_GELLIED"),
#                 ("GRACE", "GRACE"), ("CHAMPTIONS", "CHAMPTIONS"), ("SPLENDOR", "SPLENDOR"), ("HOPE", "HOPE"), ("LOVE", "LOVE"))
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

    class Meta:
        ordering = ['-store_rank']


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to="images/profile-images/", null=True)
    phone_number = models.CharField(max_length=16)
    gender = models.CharField(max_length=10, choices=GENDER_LISTS)
    is_student = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    # location = models.PointField(null=True) # Spatial Field Types

    def __str__(self) -> str:
        return self.user.username


class Vendor(models.Model):
    user = models.OneToOneField(Profile, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return self.user.username


class Hostel(models.Model):
    name = models.CharField(max_length=50)
    short_name = models.CharField(max_length=10, null=True, blank=True)
    gender = models.CharField(
        max_length=10, choices=GENDER_LISTS, null=True, blank=True)
    is_floor = models.BooleanField(default=False)
    floor_count = models.IntegerField(default=0)

    def __str__(self) -> str:
        return self.name


class Client(models.Model):
    user = models.OneToOneField(Profile, on_delete=models.CASCADE)
    hostel = models.ForeignKey(Hostel, on_delete=models.SET_NULL, null=True)
    room = models.CharField(max_length=20)


class Deliverer(models.Model):
    user = models.OneToOneField(Profile, on_delete=models.CASCADE)


@receiver(post_save, sender=User)
def update_profile_signal(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    instance.profile.save()
