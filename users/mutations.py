import graphene
from graphql import GraphQLError
from .types import VendorType
from .models import Vendor, Store


class CreateVendorMutation(graphene.Mutation):
    class Arguments:
        # The input arguments for this mutation
        store_name = graphene.String(required=True)
        store_nickname = graphene.String()
        store_category = graphene.String(required=True)
        store_abbv = graphene.String()

    # The class attributes define the response of the mutation
    vendor = graphene.Field(VendorType)

    @staticmethod
    def mutate(self, info, store_name, store_category, store_nickname=None, store_abbv=None):
        vendor = Vendor.objects.filter(user=info.context.user.profile).first()
        if vendor is None:
            store = Store.objects.create(
                store_name=store_name,
                store_nickname=store_nickname,
                store_category=store_category,
                store_abbv=store_abbv
            )
            store.save()
            vendor = Vendor.objects.create(
                user=info.context.user.profile,
                store=store)
            vendor.save()
        else:
            raise GraphQLError('You Already A Vendor')
        # Notice we return an instance of this mutation
        return CreateVendorMutation(vendor=vendor)


class EditVendorMutation(graphene.Mutation):
    class Arguments:
        # The input arguments for this mutation
        id = graphene.ID()
        full_name = graphene.String()
        gender = graphene.String()
        phone_number = graphene.String()
        email = graphene.String()

    # The class attributes define the response of the mutation
    vendor = graphene.Field(VendorType)

    def mutate(self, info, id, full_name, gender, phone_number, email):

        vendor = Vendor.objects.get(pk=id)
        vendor.full_name = full_name
        vendor.gender = gender
        vendor.phone_number = phone_number
        vendor.email = email
        vendor.save()
        # Notice we return an instance of this mutation
        return EditVendorMutation(vendor=vendor)
