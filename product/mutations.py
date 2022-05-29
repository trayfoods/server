import graphene
from graphql import GraphQLError
from product.models import Item, ItemImage, ItemAttribute
from product.types import ItemType
from users.models import Vendor

from graphene_file_upload.scalars import Upload


class AddProductMutation(graphene.Mutation):
    class Arguments:
        # The input arguments for this mutation
        product_name = graphene.String(required=True)
        product_price = graphene.Int(required=True)
        product_type = graphene.String(required=True)
        product_category = graphene.String(required=True)
        product_desc = graphene.String()
        product_calories = graphene.Int()

        product_image = Upload(required=True)

    # The class attributes define the response of the mutation
    product = graphene.Field(ItemType)

    def mutate(self, info, product_name, product_price, product_category, product_type, product_image, product_desc=None, product_calories=None):
        store = Vendor.objects.filter(
            user=info.context.user.profile).first().store
        product = Item.objects.filter(
            product_name=product_name.strip()).first()
        qsr = Vendor.objects.filter(user=info.context.user.profile).first()
        if qsr is None:
            raise GraphQLError("You Need To Become A Vendor To Add New Item")
        if product and product.product_creator == qsr:
            raise GraphQLError("Item Already In Your Store", product)
        else:
            product_category = ItemAttribute.objects.filter(
                urlParamName=product_category).first()
            product_type = ItemAttribute.objects.filter(
                urlParamName=product_type).first()
            if product is None and not qsr is None and not product_category is None and not product_type is None:
                print(product_image)
                product = Item.objects.create(product_name=product_name.strip(), product_price=product_price, product_category=product_category, product_type=product_type,
                                              product_desc=product_desc, product_calories=product_calories, product_creator=qsr).save()
                product = Item.objects.filter(
                    product_name=product_name.strip()).first()
                qs = ItemImage.objects.filter(product=product).first()
                is_primary = True
                if qs:
                    is_primary = False
                productImage = ItemImage.objects.create(
                    product=product, item_image=product_image, is_primary=is_primary)
                productImage.save()
                product.product_avaliable_in.add(qsr.store)
                product.product_images.add(productImage)
                product.save()
        store.store_products.add(product)
        # Notice we return an instance of this mutation
        return AddProductMutation(product=product)


class EditAvaliableProductsMutation(graphene.Mutation):
    class Arguments:
        # The input arguments for this mutation
        products = graphene.String(required=True)

    # The class attributes define the response of the mutation
    product = graphene.List(ItemType)

    def mutate(self, info, products):
        products = products.split(',')
        product_list = []
        for item in products:
            product = Item.objects.filter(product_name=item.strip()).first()
            product_list.append(product)
            qsr = Vendor.objects.filter(user=info.context.user.profile).first()
            if not product is None and not qsr is None:
                product.product_avaliable_in.add(qsr.store)
                product.save()
        # Notice we return an instance of this mutation
        return EditAvaliableProductsMutation(product=product_list)
