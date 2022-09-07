import graphene
from graphql import GraphQLError
from product.models import Item, ItemImage, ItemAttribute
from product.types import ItemType
from users.models import Vendor, Store
from django.shortcuts import get_object_or_404
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

        product_images = Upload(required=True)

    # The class attributes define the response of the mutation
    product = graphene.Field(ItemType)
    success = graphene.Boolean()

    def mutate(self, info, product_name, product_price, product_category, product_type, product_images, product_slug, product_desc=None, product_calories=None):
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
            if not product is None:
                success = False
                is_vendor_in_product_ava = product.product_avaliable_in.filter(
                    store_nickname=vendor.store.store_nickname).first()
                if not is_vendor_in_product_ava is None:
                    raise GraphQLError("Item Already In Your Store")
                elif product.product_creator == vendor and is_vendor_in_product_ava is None:
                    store.store_products.add(product)
                    success = True
                elif product.product_creator == vendor and not is_vendor_in_product_ava is None:
                    raise GraphQLError("Item Already In Your Store")

            else:
                product_category = ItemAttribute.objects.filter(
                    urlParamName=product_category).first()
                product_type = ItemAttribute.objects.filter(
                    urlParamName=product_type).first()
                if product is None and not vendor is None and not product_category is None and not product_type is None:
                    # Checking if sulg already exists
                    if not Item.objects.filter(product_slug=product_slug).first() is None:
                        product = Item.objects.create(product_name=product_name.strip(), product_price=product_price, product_category=product_category, product_type=product_type,
                                                      product_desc=product_desc, product_calories=product_calories, product_creator=vendor)
                    else:
                        product = Item.objects.create(product_slug=product_slug, product_name=product_name.strip(), product_price=product_price, product_category=product_category, product_type=product_type,
                                                      product_desc=product_desc, product_calories=product_calories, product_creator=vendor)
                    product.save()
                    # product = Item.objects.filter(
                    #     product_name=product_name.strip()).first()
                    for product_image in product_images:
                        qs = ItemImage.objects.filter(product=product).first()
                        is_primary = True
                        if not qs is None:
                            is_primary = False
                        productImage = ItemImage.objects.create(
                            product=product, item_image=product_image, is_primary=is_primary)
                        productImage.save()
                        product = Item.objects.filter(
                            product_name=product_name.strip()).first()
                        if not product is None:
                            product.product_avaliable_in.add(vendor.store)
                            product.product_images.add(productImage)
                            product.save()
            store.store_products.add(product)
            success = True
        else:
            raise GraphQLError("Login required.")
        # Notice we return an instance of this mutation
        return AddProductMutation(product=product, success=success)


# Allowing Vendors to Select Multiple Product As Avaliable Products
class AddMultipleAvaliableProductsMutation(graphene.Mutation):
    class Arguments:
        # The input arguments for this mutation
        products = graphene.String(required=True)
        action = graphene.String(required=True)

    # The class attributes define the response of the mutation
    product = graphene.List(ItemType)
    success = graphene.Boolean()

    def mutate(self, info, products, action):
        success = False
        product_list = None
        if info.context.user.is_authenticated:
            products = products.split(',')
            for item in products:
                product = Item.objects.filter(
                    product_slug=item.strip()).first()
                product_list.append(product)
                vendor = Vendor.objects.filter(
                    user=info.context.user.profile).first()
                # Checking if the current user is equals to the store vendor
                # Then add 0.5 to the store_rank
                try:
                    if not product.product_creator is None:
                        if product.product_creator != vendor:
                            store = Store.objects.filter(
                                store_nickname=product.product_creator.store.store_nickname).first()
                            if not store is None:
                                store.store_rank += 0.5
                                store.save()
                except:
                    pass
                if not product is None and not vendor is None:
                    if action == "add":
                        product.product_avaliable_in.add(vendor.store)
                        vendor.store.store_products.add(product)
                    elif action == "remove":
                        product.product_avaliable_in.remove(vendor.store)
                        vendor.store.store_products.remove(product)
                    else:
                        raise GraphQLError(
                            "Enter either `add/remove` for actions.")
                    product.save()
                    success = True
        else:
            raise GraphQLError("Login required.")
        # Notice we return an instance of this mutation
        return AddMultipleAvaliableProductsMutation(product=product_list, success=success)


# This Mutation Only Add One Product to the storeProducts as available
class AddAvaliableProductMutation(graphene.Mutation):
    class Arguments:
        # The input arguments for this mutation
        product_slug = graphene.String(required=True)
        action = graphene.String(required=True)

    # The class attributes define the response of the mutation
    product = graphene.Field(ItemType)
    success = graphene.Boolean()

    def mutate(self, info, product_slug, action):
        success = False
        if info.context.user.is_authenticated:
            product = Item.objects.filter(
                product_slug=product_slug.strip()).first()
            vendor = Vendor.objects.filter(
                user=info.context.user.profile).first()
            # Checking if the current user is equals to the store vendor
            # Then add 0.5 to the store_rank
            try:
                if not product.product_creator is None:
                    if product.product_creator != vendor:
                        store = Store.objects.filter(
                            store_nickname=product.product_creator.store.store_nickname).first()
                        if not store is None:
                            store.store_rank += 0.5
                            store.save()
            except:
                pass
            if not product is None and not vendor is None:
                store = get_object_or_404(Store, id=vendor.store.id)
                if action == "add":
                    vendor.store.store_products.add(product)
                    product.product_avaliable_in.add(store)
                elif action == "remove":
                    vendor.store.store_products.remove(product)
                    product.product_avaliable_in.remove(store)
                else:
                    raise GraphQLError(
                        "Enter either `add/remove` for actions.")
                product.save()
                success = True
        else:
            raise GraphQLError("Login required.")
        # Notice we return an instance of this mutation
        return AddAvaliableProductMutation(product=product, success=success)


# This Mutation adds +1 to the product_clicks value,
# Then also add rank to the store owner of the product
class AddProductClickMutation(graphene.Mutation):
    class Arguments:
        slug = graphene.String(required=True)

    success = graphene.Boolean()
    item = graphene.Field(ItemType)

    def mutate(self, info, slug):
        success = False
        item = Item.objects.filter(product_slug=slug).first()
        if not item is None:
            if item.product_creator:
                store = Store.objects.filter(
                    store_nickname=item.product_creator.store.store_nickname).first()
                if not store is None:
                    store.store_rank += 0.5
                    store.save()
            item.product_clicks += 1
            item.save()
            success = True

        return AddProductClickMutation(item=item, success=success)
