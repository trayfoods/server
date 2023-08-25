from django.utils import timezone
from django.conf import settings
import graphene
from graphql import GraphQLError
from product.models import Item, ItemImage, ItemAttribute, Order, Rating, filter_comment
from product.types import ItemType
from users.models import UserActivity, Vendor, Store
from graphene_file_upload.scalars import Upload
from .types import ShippingInputType, OrderType, RatingInputType

from trayapp.permissions import IsAuthenticated, permission_checker

import json

from graphql_auth.decorators import verification_required

PAYSTACK_SECRET_KEY = settings.PAYSTACK_SECRET_KEY


class Output:
    """
    A class to all public classes extend to
    padronize the output
    """

    success = graphene.Boolean(default_value=False)
    error = graphene.String(default_value=None)


class AddProductMutation(Output, graphene.Mutation):
    class Arguments:
        # The input arguments for this mutation
        product_slug = graphene.String(required=True)
        product_name = graphene.String(required=True)
        product_price = graphene.Int(required=True)
        product_type = graphene.String(required=True)
        product_category = graphene.String(required=True)
        product_share_visibility = graphene.String(required=True)
        product_calories = graphene.Int()
        product_desc = graphene.String()
        product_qty = graphene.Int()
        product_qty_unit = graphene.String()
        is_groupable = graphene.Boolean()

        product_images = Upload(required=True)

    # The class attributes define the response of the mutation
    product = graphene.Field(ItemType)

    @permission_checker([IsAuthenticated])
    def mutate(
        self,
        info,
        **kwargs,
    ):
        list_of_required_fields = [
            "product_slug",
            "product_name",
            "product_price",
            "product_type",
            "product_category",
            "product_share_visibility",
            "product_images",
        ]

        if not kwargs.get("product_qty") is None:
            list_of_required_fields.append("product_qty_unit")

        # check if all the required fields are present
        for field in list_of_required_fields:
            if field not in kwargs:
                raise GraphQLError(f"{field} is required.")

        kwargs = {
            k: v for k, v in kwargs.items() if v is not None
        }  # remove all None values from kwargs

        product_slug = kwargs.get("product_slug")
        product_name = kwargs.get("product_name")
        product_images = kwargs.get("product_images")
        product_category_val = kwargs.get("product_category")
        product_type_val = kwargs.get("product_type")

        # remove category, type and images from kwargs
        kwargs.pop("product_category")
        kwargs.pop("product_type")
        kwargs.pop("product_images")

        success = False
        product = None
        vendor = Vendor.objects.filter(user=info.context.user.profile).first()
        if vendor is None:
            success = False
            raise GraphQLError("You Need To Become A Vendor To Add New Item")

        product = Item.objects.filter(
            product_slug=product_slug.strip(), product_name=product_name.strip()
        ).first()

        if not product is None:
            success = False
            raise GraphQLError("Item Already Exists")

        try:
            product_category = ItemAttribute.objects.filter(
                urlParamName=product_category_val
            ).first()
            product_type = ItemAttribute.objects.filter(
                urlParamName=product_type_val
            ).first()
            if product is None and not vendor is None:
                # spread the kwargs
                save_data = {
                    **kwargs,
                    # "product_slug": product_slug.strip(),
                    # "product_name": product_name.strip(),
                    "product_category": product_category,
                    "product_type": product_type,
                    "product_creator": vendor,
                }

                # Checking if slug already exists
                if not Item.objects.filter(product_slug=product_slug.strip()).exists():
                    product = Item.objects.create(
                        **save_data,
                    )
                    product.save()
                else:
                    save_data.pop("product_slug")
                    # if slug already exists, add a random string to the slug
                    new_slug = kwargs.get("product_slug").strip() + str(
                        timezone.now().timestamp()
                    )
                    product = Item.objects.create(
                        **save_data,
                        product_slug=new_slug,
                    )
                    product.save()

                # check if the product has been created
                if product is None:
                    raise GraphQLError("Item Not Created")

                # Adding the product images
                for product_image in product_images:
                    qs = ItemImage.objects.filter(product=product).first()
                    is_primary = True
                    if not qs is None:
                        is_primary = False
                    productImage = ItemImage.objects.create(
                        product=product,
                        item_image=product_image,
                        is_primary=is_primary,
                    )
                    productImage.save()
                    product.product_avaliable_in.add(vendor.store)
                    product.product_images.add(productImage)
                    product.save()
        except Exception as e:
            raise GraphQLError(e)
        # Notice we return an instance of this mutation
        return AddProductMutation(product=product, success=success)

    # @verification_required
    def resolve_mutation(cls, root, info, **kwargs):
        # get the product slug
        product_slug = kwargs.get("product_slug")
        # get the product
        product = Item.objects.filter(product_slug=product_slug).first()
        # check if product have all the required fields

        if (
            product.product_name is None
            and product.product_price is None
            and product.product_category is None
            and product.product_type is None
            and product.product_share_visibility is None
            and product.product_creator is None
            # check if the product have at least one image
            and product.product_images.all().count() <= 0
        ):
            product.delete()
            raise GraphQLError("Product Not Created")

        return cls(product=product, success=True)


# Allowing Vendors to Select Multiple Product As Avaliable Products
class AddMultipleAvaliableProductsMutation(graphene.Mutation):
    class Arguments:
        # The input arguments for this mutation
        products = graphene.String(required=True)
        action = graphene.String(required=True)

    # The class attributes define the response of the mutation
    product = graphene.List(ItemType)
    success = graphene.Boolean()

    @permission_checker([IsAuthenticated])
    def mutate(self, info, products, action):
        success = False
        product_list = None
        if info.context.user.is_authenticated:
            products = products.split(",")
            for item in products:
                product = Item.objects.filter(product_slug=item.strip()).first()
                product_list.append(product)
                vendor = Vendor.objects.filter(user=info.context.user.profile).first()
                # Checking if the current user is equals to the store vendor
                # Then add 0.5 to the store_rank
                try:
                    if not product.product_creator is None:
                        if product.product_creator != vendor:
                            store = Store.objects.filter(
                                store_nickname=product.product_creator.store.store_nickname
                            ).first()
                            if not store is None:
                                store.store_rank += 0.5
                                store.save()
                except:
                    pass
                if not product is None and not vendor is None:
                    if action == "add":
                        product.product_avaliable_in.add(vendor.store)
                    elif action == "remove":
                        product.product_avaliable_in.remove(vendor.store)
                    else:
                        raise GraphQLError("Enter either `add/remove` for actions.")
                    product.save()
                    success = True
        else:
            raise GraphQLError("Login required.")
        # Notice we return an instance of this mutation
        return AddMultipleAvaliableProductsMutation(
            product=product_list, success=success
        )


# This Mutation Only Add One Product to the storeProducts as available
class AddAvaliableProductMutation(graphene.Mutation):
    class Arguments:
        # The input arguments for this mutation
        product_slug = graphene.String(required=True)
        action = graphene.String(required=True)

    # The class attributes define the response of the mutation
    product = graphene.Field(ItemType)
    success = graphene.Boolean()

    @permission_checker([IsAuthenticated])
    def mutate(self, info, product_slug, action):
        success = False
        product = Item.objects.filter(product_slug=product_slug.strip()).first()
        user = info.context.user
        profile = user.profile
        # Checking if the current user is equals to the store vendor
        # Then add 0.5 to the store_rank
        if not product is None and user.profile.is_vendor:
            vendor = profile.vendor
            if (
                product.product_creator != vendor
                and product.product_share_visibility == "private"
            ):  # then check if the user is a vendor
                raise GraphQLError(
                    "You are not allowed to add this product to your store."
                )
            try:
                if not product.product_creator is None:
                    if product.product_creator != vendor:
                        store = Store.objects.filter(
                            store_nickname=product.product_creator.store.store_nickname
                        ).first()
                        if not store is None:
                            store.store_rank += 0.5
                            store.save()
            except:
                pass
            store = vendor.store
            if action == "add":
                new_activity = UserActivity.objects.create(
                    user_id=info.context.user.id,
                    activity_message=f"Added {product.product_name} as avaliable product",
                    activity_type="add_to_items",
                    item=product,
                    timestamp=timezone.now(),
                )
                product.product_avaliable_in.add(store)
                product.save()
                new_activity.save()
            elif action == "remove":
                new_activity = UserActivity.objects.create(
                    user_id=info.context.user.id,
                    activity_message=f"Removed {product.product_name} as avaliable product",
                    activity_type="remove_from_items",
                    item=product,
                    timestamp=timezone.now(),
                )
                product.product_avaliable_in.remove(store)
                product.save()
                new_activity.save()
            else:
                raise GraphQLError("Enter either `add/remove` for actions.")
            success = True
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
        if not item is None and info.context.user.is_authenticated:
            new_activity = UserActivity.objects.create(
                user_id=info.context.user.id,
                activity_message=None,
                activity_type="click",
                item=item,
                timestamp=timezone.now(),
            )
            if item.product_creator:
                store = Store.objects.filter(
                    store_nickname=item.product_creator.store.store_nickname
                ).first()
                if not store is None:
                    store.store_rank += 0.5
                    store.save()
            item.product_clicks += 1
            item.save()
            new_activity.save()
            success = True

        return AddProductClickMutation(item=item, success=success)


class CreateOrderMutation(graphene.Mutation):
    class Arguments:
        overall_price = graphene.Float(required=True)
        delivery_price = graphene.Float(required=True)
        shipping = ShippingInputType(required=True)
        linked_items = graphene.List(graphene.String, required=True)
        stores_infos = graphene.JSONString(required=True)

    order = graphene.Field(OrderType)
    success = graphene.Boolean(default_value=False)
    unavailable_items = graphene.List(graphene.String)

    @permission_checker([IsAuthenticated])
    def mutate(self, info, **kwargs):
        overall_price = kwargs.get("overall_price")
        delivery_price = kwargs.get("delivery_price")
        shipping = kwargs.get("shipping")
        linked_items = kwargs.get("linked_items")
        stores_infos = kwargs.get("stores_infos")

        shipping = json.dumps(shipping)
        stores_infos = json.dumps(stores_infos)

        # check if all the items are avaliable
        unavailable_items = []
        available_items = []
        for item in linked_items:
            item = Item.objects.filter(product_slug=item).first()
            if item is None:
                raise GraphQLError(
                    "Order contains invalid items, clear cart and retry."
                )
            if item.product_avaliable_in.count() <= 0:
                unavailable_items.append(item.product_slug)

            available_items.append(item)

        available_stores = []
        stores_infos_json = json.loads(stores_infos)
        for store in stores_infos_json:
            storeId = store["storeId"]
            store = Store.objects.filter(store_nickname=storeId).first()
            if store is None:
                raise GraphQLError(
                    "Order contains invalid stores, clear cart and retry."
                )
            available_stores.append(store)

        if len(unavailable_items) > 0:
            return CreateOrderMutation(
                order=None, success=False, unavailable_items=unavailable_items
            )

        current_user = info.context.user
        order_payment_status = None

        overall_price = float(overall_price) + 10.0

        create_order = Order.objects.create(
            user=current_user,
            overall_price=overall_price,
            delivery_price=delivery_price,
            shipping=shipping,
            stores_infos=stores_infos,
            order_payment_status=order_payment_status,
        )
        create_order.linked_stores.set(available_stores)
        create_order.linked_items.set(available_items)
        create_order.save()

        return CreateOrderMutation(order=create_order, success=True)


class RateItemMutation(graphene.Mutation):
    class Arguments:
        item_slug = graphene.ID(required=True)
        rating = graphene.Argument(RatingInputType, required=True)

    success = graphene.Boolean()
    review_id = graphene.ID()

    @staticmethod
    @permission_checker([IsAuthenticated])
    def mutate(root, info, item_slug, rating):
        user = info.context.user
        try:
            item = Item.objects.get(product_slug=item_slug)
            try:
                rating_qs = Rating.objects.get(user=user, item=item)
                rating_qs.stars = rating.stars
                rating_qs.comment = filter_comment(rating.comment)
                rating_qs.save()
                return RateItemMutation(success=True, review_id=rating_qs.id)
            except Rating.DoesNotExist:
                new_rating = Rating.objects.create(
                    user=user, item=item, stars=rating.stars, comment=rating.comment
                )
                new_rating.save()
                return RateItemMutation(success=True, review_id=new_rating.id)
        except Item.DoesNotExist:
            raise ValueError("Invalid Item Slug")


class DeleteRatingMutation(graphene.Mutation):
    class Arguments:
        item_slug = graphene.ID(required=True)

    success = graphene.Boolean()

    @staticmethod
    @permission_checker([IsAuthenticated])
    def mutate(root, info, item_slug):
        user = info.context.user
        try:
            item = Item.objects.get(product_slug=item_slug)
            try:
                rating_qs = Rating.objects.get(user=user, item=item)
                rating_qs.delete()
            except Rating.DoesNotExist:
                raise ValueError("Rating Does Not Exist")
        except Item.DoesNotExist:
            raise ValueError("Invalid Item Slug")

        return DeleteRatingMutation(success=True)


class HelpfulReviewMutation(graphene.Mutation):
    class Arguments:
        review_id = graphene.ID(required=True)
        helpful = graphene.Boolean(required=True)

    success = graphene.Boolean()

    @staticmethod
    @permission_checker([IsAuthenticated])
    def mutate(root, info, review_id, helpful):
        user = info.context.user
        try:
            rating = Rating.objects.get(id=review_id, user=user)
            # update rating users_liked
            if helpful:
                rating.users_liked.add(user)
            else:
                rating.users_liked.remove(user)
            rating.save()
        except Rating.DoesNotExist:
            raise ValueError("Invalid Rating Id")

        return HelpfulReviewMutation(success=True)


class InitializeTransactionMutation(graphene.Mutation):
    class Arguments:
        order_id = graphene.ID(required=True)

    success = graphene.Boolean(default_value=False)
    transaction_id = graphene.String()
    payment_url = graphene.String()

    @staticmethod
    @permission_checker([IsAuthenticated])
    def mutate(root, info, order_id):
        order = Order.objects.filter(order_track_id=order_id).first()

        # check if order exists
        if order is None:
            raise ValueError("Invalid Order Id")

        try:
            response = order.create_payment_link

            if response["status"] and response["status"] == True:
                transaction_id = response["data"]["reference"]
                payment_url = response["data"]["authorization_url"]

                return InitializeTransactionMutation(
                    success=True, transaction_id=transaction_id, payment_url=payment_url
                )
            else:
                raise GraphQLError(response["message"])
        except Exception as e:
            print(e)
            raise GraphQLError("An error occured while initializing transaction")
