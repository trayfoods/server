# import graphene
from dataclasses import fields
from profile import Profile
import graphene
from graphene_django.types import DjangoObjectType
from django.contrib.auth.models import User
from .models import Client, Vendor, Store, Profile


class UserType(DjangoObjectType):
    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "is_active"]


class ClientType(DjangoObjectType):
    class Meta:
        model = Client
        fields = '__all__'


class ProfileType(DjangoObjectType):
    class Meta:
        model = Profile
        fields = '__all__'
    
    def resolve_image(self, info, *args, **kwargs):
        image = info.context.build_absolute_uri(self.image.url)
        return image


class VendorType(DjangoObjectType):
    profile = graphene.Field(ProfileType)

    class Meta:
        model = Vendor
        fields = ['id','profile', 'store']

    def resolve_profile(self, info):
        request = info.context
        user = Profile.objects.filter(user=request.user).first()
        print(user)
        return user


class StoreType(DjangoObjectType):
    class Meta:
        model = Store
        fields = ['store_name', 'store_category',
                  'store_abbv', 'store_nickname', 'store_products']
