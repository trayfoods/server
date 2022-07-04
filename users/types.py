from profile import Profile
import graphene
from graphene_django.types import DjangoObjectType
from django.contrib.auth.models import User
from .models import Client, Vendor, Store, Profile, Hostel


class UserType(DjangoObjectType):
    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "is_active"]


class HostelType(DjangoObjectType):
    class Meta:
        model = Hostel
        fields = '__all__'

class ClientType(DjangoObjectType):
    class Meta:
        model = Client
        fields = '__all__'


class ProfileType(DjangoObjectType):
    class Meta:
        model = Profile
        fields = '__all__'

    def resolve_image(self, info, *args, **kwargs):
        if self.image:
            image = info.context.build_absolute_uri(self.image.url)
        else:
            image = None
        return image


class VendorType(DjangoObjectType):
    profile = graphene.Field(ProfileType)

    class Meta:
        model = Vendor
        fields = ['id', 'profile', 'store']

    def resolve_profile(self, info):
        user = Profile.objects.filter(user=self.user.user).first()
        return user


class StoreType(DjangoObjectType):
    vendor = graphene.Field(VendorType)
    class Meta:
        model = Store
        fields = ['store_name', 'store_category','vendor',
                  'store_rank', 'store_nickname', 'store_products']
    
    def resolve_vendor(self, info):
        vendor = Vendor.objects.filter(store=self).first()
        return vendor

    def resolve_store_products(self, info):
        qs = self.store_products.all()
        storeProducts = []
        for item in qs:
            item.product_avaliable_in.set([self])
            storeProducts.append(item)
        return storeProducts
        
