import graphene
from graphql import GraphQLError
from product.models import Item, ItemImage, ItemAttribute
from product.types import ItemType
from users.models import Vendor

from graphene_file_upload.scalars import Upload


class AddProductMutation(graphene.Mutation):
    class Arguments:
        # The input arguments for this mutation
        product_slug = graphene.String(required=True)
        product_name = graphene.String(required=True)
        product_price = graphene.Int(required=True)
        product_type = graphene.String(required=True)
        product_category = graphene.String(required=True)
        product_desc = graphene.String()
        product_calories = graphene.Int()

        product_image = Upload(required=True)

    # The class attributes define the response of the mutation
    product = graphene.Field(ItemType)
    success = graphene.Boolean()

    def mutate(self, info, product_name, product_price, product_category, product_type, product_image, product_slug, product_desc=None, product_calories=None):
        success = False
        product = None
        if info.context.user.is_authenticated:
            store = Vendor.objects.filter(
                user=info.context.user.profile).first().store
            product = Item.objects.filter(
                product_name=product_name.strip()).first()
            vendor = Vendor.objects.filter(
                user=info.context.user.profile).first()
            if vendor is None:
                success = False
                raise GraphQLError(
                    "You Need To Become A Vendor To Add New Item")
            if product and product.product_creator == vendor:
                success = False
                raise GraphQLError("Item Already In Your Store")
            else:
                product_category = ItemAttribute.objects.filter(
                    urlParamName=product_category).first()
                product_type = ItemAttribute.objects.filter(
                    urlParamName=product_type).first()
                if product is None and not vendor is None and not product_category is None and not product_type is None:
                    if not Item.objects.filter(product_slug=product_slug).first() is None:
                        product = Item.objects.create(product_name=product_name.strip(), product_price=product_price, product_category=product_category, product_type=product_type,
                                                      product_desc=product_desc, product_calories=product_calories, product_creator=vendor)
                    else:
                        product = Item.objects.create(product_slug=product_slug, product_name=product_name.strip(), product_price=product_price, product_category=product_category, product_type=product_type,
                                                      product_desc=product_desc, product_calories=product_calories, product_creator=vendor)
                    product.save()
                    # product = Item.objects.filter(
                    #     product_name=product_name.strip()).first()
                    qs = ItemImage.objects.filter(product=product).first()
                    is_primary = True
                    if not qs is None:
                        is_primary = False
                    productImage = ItemImage.objects.create(
                        product=product, item_image=product_image, is_primary=is_primary)
                    productImage.save()
                    print(productImage)
                    product.product_avaliable_in.add(vendor.store)
                    product.product_images.add(productImage)
                    product.save()
            store.store_products.add(product)
            success = True
        else:
            raise GraphQLError("Login required.")
        # Notice we return an instance of this mutation
        return AddProductMutation(product=product, success=success)


class EditAvaliableProductsMutation(graphene.Mutation):
    class Arguments:
        # The input arguments for this mutation
        products = graphene.String(required=True)

    # The class attributes define the response of the mutation
    product = graphene.List(ItemType)
    success = graphene.Boolean()

    def mutate(self, info, products):
        success = False
        product_list = None
        if info.context.user.is_authenticated:
            products = products.split(',')
            for item in products:
                product = Item.objects.filter(
                    product_name=item.strip()).first()
                product_list.append(product)
                vendor = Vendor.objects.filter(
                    user=info.context.user.profile).first()
                if not product is None and not vendor is None:
                    product.product_avaliable_in.add(vendor.store)
                    product.save()
                    success = True
        else:
            raise GraphQLError("Login required.")
        # Notice we return an instance of this mutation
        return EditAvaliableProductsMutation(product=product_list, success=success)
