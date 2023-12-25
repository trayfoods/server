from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
from django.conf import settings
import graphene
from graphql import GraphQLError
from product.models import Item, ItemImage, ItemAttribute, Order, Rating, filter_comment
from product.types import ItemType
from users.models import UserActivity, Store
from graphene_file_upload.scalars import Upload
from .types import ShippingInputType, OrderType, RatingInputType

from trayapp.permissions import IsAuthenticated, permission_checker

import json

PAYSTACK_SECRET_KEY = settings.PAYSTACK_SECRET_KEY


class Output:
    """
    A class to all public classes extend to
    padronize the output
    """

    success = graphene.Boolean(default_value=False)
    error = graphene.String(default_value=None)


from django.db import transaction, IntegrityError


class AddProductMutation(Output, graphene.Mutation):
    class Arguments:
        product_qty = graphene.Int()
        product_desc = graphene.String()
        is_groupable = graphene.Boolean()
        product_calories = graphene.Float()
        product_qty_unit = graphene.String()
        product_images = Upload(required=True)
        product_name = graphene.String(required=True)
        product_slug = graphene.String(required=True)
        product_type = graphene.String(required=True)
        product_price = graphene.Decimal(required=True)
        store_menu_name = graphene.String(required=True)
        product_category = graphene.String(required=True)
        product_share_visibility = graphene.String(required=True)

    product = graphene.Field(ItemType, default_value=None)

    @permission_checker([IsAuthenticated])
    def mutate(self, info, **kwargs):
        list_of_required_fields = [
            "product_slug",
            "product_name",
            "product_price",
            "product_type",
            "product_category",
            "product_share_visibility",
            "product_images",
            "store_menu_name",
        ]

        if not kwargs.get("product_qty") is None and kwargs.get("product_qty") > 0:
            list_of_required_fields.append("product_qty_unit")

        # Check if all the required fields are present
        for field in list_of_required_fields:
            if (
                field not in kwargs
                or kwargs.get(field) is None
                or kwargs.get(field) == ""
            ):
                field = str(field).replace("_", " ").capitalize()
                return AddProductMutation(error=f"{field} is required.")

        kwargs = {
            k: v for k, v in kwargs.items() if v is not None
        }  # Remove None values from kwargs

        product_slug = kwargs.get("product_slug")
        product_name = kwargs.get("product_name")
        product_images = kwargs.get("product_images")
        product_category_val = kwargs.get("product_category")
        product_type_val = kwargs.get("product_type")

        # Remove category, type and images from kwargs
        kwargs.pop("product_category")
        kwargs.pop("product_type")
        kwargs.pop("product_images")

        profile = info.context.user.profile
        if profile.store is None:
            return AddProductMutation(error="You are not a vendor")

        proudct_menu_name = kwargs.get("store_menu_name", "Others")
        if not proudct_menu_name in profile.store.store_menu:
            return AddProductMutation(error="Invalid Menu Name")

        product = (
            Item.get_items()
            .filter(
                product_slug=product_slug.strip(), product_name=product_name.strip()
            )
            .first()
        )

        if not product is None:
            return AddProductMutation(error="Product Already Exists")

        with transaction.atomic():
            try:
                product_category = ItemAttribute.objects.get(
                    urlParamName=product_category_val
                )
                product_type = ItemAttribute.objects.get(urlParamName=product_type_val)

                if product is None and not profile is None:
                    # Spread the kwargs
                    save_data = {
                        **kwargs,
                        "product_creator": profile.store,
                        "product_category": product_category,
                        "product_type": product_type,
                        "has_qty": kwargs.get("product_qty")
                        and kwargs.get("product_qty", 0) > 0,
                    }

                    # Checking if slug already exists
                    if (
                        not Item.get_items()
                        .filter(product_slug=product_slug.strip())
                        .exists()
                    ):
                        product = Item.objects.create(**save_data)
                        product.save()
                    else:
                        save_data.pop("product_slug")
                        new_slug = kwargs.get("product_slug").strip() + str(
                            timezone.now().timestamp()
                        )
                        product = Item.objects.create(
                            **save_data, product_slug=new_slug
                        )
                        product.save()

                    # Check if the product has been created
                    if product is None:
                        raise GraphQLError("An error occured while creating product")

                    # Optimize Image Handling
                    item_images = [
                        ItemImage(
                            product=product, item_image=image, is_primary=is_primary
                        )
                        for image, is_primary in zip(
                            # convert to list to avoid multiple iteration
                            product_images,
                            [True] + [False] * (len(product_images) - 1),
                        )
                    ]
                    ItemImage.objects.bulk_create(item_images)

                return AddProductMutation(product=product, success=True)
            except IntegrityError as e:
                raise GraphQLError(e)

            except ItemAttribute.DoesNotExist:
                raise GraphQLError("Invalid Category or Type")

            except Exception as e:
                raise GraphQLError(e)


# This Mutation Only Add One Product to the storeProducts as available
class ItemCopyDeleteMutation(Output, graphene.Mutation):
    class Arguments:
        # The input arguments for this mutation
        slug = graphene.String(required=True)
        action = graphene.String(required=True)

    @permission_checker([IsAuthenticated])
    def mutate(self, info, slug, action):
        product_slug = slug.strip()
        product = Item.get_items().filter(product_slug=product_slug).first()
        user = info.context.user
        profile = user.profile

        if product is None:
            return ItemCopyDeleteMutation(error="Item does not exist")

        if not profile.is_vendor:
            return ItemCopyDeleteMutation(error="You are not a vendor")

        is_owner = product.product_creator == profile.store
        is_public = product.product_share_visibility == "public"

        # Checking if the current user is equals to the store vendor
        # Then add 0.5 to the store_rank
        if not is_owner and not is_public:  # then check if the user is a vendor
            return ItemCopyDeleteMutation(
                error=f"You are not allowed to {action} this item"
            )

        if (is_public or is_owner) and action == "copy":
            # increase the rank of the creator store by 0.5
            store = product.product_creator
            store.store_rank += 0.5
            store.save()
            return ItemCopyDeleteMutation(success=True)

        elif is_owner and action == "delete":
            product.product_status = "deleted"
            product.save()
            return ItemCopyDeleteMutation(success=True)
        else:
            raise GraphQLError("Enter either `copy` or ``delete for actions.")


class UpdateItemMenuMutation(Output, graphene.Mutation):
    class Arguments:
        slug = graphene.String(required=True)
        menu = graphene.String(required=True)

    @permission_checker([IsAuthenticated])
    def mutate(self, info, slug, menu):
        user = info.context.user

        if not "VENDOR" in user.roles:
            return UpdateItemMenuMutation(error="You are not a vendor")

        item = Item.get_items().filter(product_slug=slug)

        if not item.exists():
            return UpdateItemMenuMutation(error="Item does not exist")

        item = item.first()

        profile = user.profile
        if item.product_creator != profile.store:
            return UpdateItemMenuMutation(error="You are not allowed to edit this item")

        if not menu in profile.store.store_menu:
            return UpdateItemMenuMutation(
                error="'{}' is not part of your menu".format(menu)
            )

        item.store_menu_name = menu
        item.save()
        return UpdateItemMenuMutation(success=True)


# This Mutation adds +1 to the product_clicks value,
# Then also add rank to the store owner of the product
class AddProductClickMutation(graphene.Mutation):
    class Arguments:
        slug = graphene.String(required=True)

    success = graphene.Boolean()
    item = graphene.Field(ItemType)

    def mutate(self, info, slug):
        success = False
        item = Item.get_items().filter(product_slug=slug).first()
        if not item is None and info.context.user.is_authenticated:
            info.context.user.profile.send_push_notification()
            new_activity = UserActivity.objects.create(
                user_id=info.context.user.id,
                activity_type="added_to_cart",
                item=item,
                timestamp=timezone.now(),
            )
            if item.product_creator:
                store = Store.objects.filter(
                    store_nickname=item.product_creator.store_nickname
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
        overall_price = graphene.Decimal(required=True)
        delivery_fee = graphene.Decimal(required=True)
        shipping = ShippingInputType(required=True)
        linked_items = graphene.List(graphene.String, required=True)
        stores_infos = graphene.JSONString(required=True)
        store_notes = graphene.JSONString()
        delivery_person_note = graphene.String()

    order = graphene.Field(OrderType)
    success = graphene.Boolean(default_value=False)
    unavailable_items = graphene.List(graphene.String)

    @permission_checker([IsAuthenticated])
    def mutate(self, info, **kwargs):
        overall_price = kwargs.get("overall_price", 0.00)
        delivery_fee = kwargs.get("delivery_fee", 0.00)
        shipping = kwargs.get("shipping")
        linked_items = kwargs.get("linked_items")
        stores_infos = kwargs.get("stores_infos")
        store_notes = kwargs.get("store_notes")
        delivery_person_note = kwargs.get("delivery_person_note")

        overall_price = Decimal(overall_price)
        delivery_fee = Decimal(delivery_fee)
        delivery_fee = delivery_fee.quantize(Decimal("1"), rounding=ROUND_HALF_UP)

        transaction_fee = Decimal(0.05) * overall_price
        transaction_fee = transaction_fee.quantize(Decimal("1"), rounding=ROUND_HALF_UP)

        shipping = json.dumps(shipping)
        stores_infos = json.dumps(stores_infos)

        # check if all the items are avaliable
        unavailable_items = []
        available_items = []
        for item in linked_items:
            item = Item.get_items().filter(product_slug=item).first()
            if item is None:
                raise GraphQLError(
                    "Order contains invalid items, clear cart and retry."
                )
            if item.product_status != "active":
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

        current_user_profile = info.context.user.profile
        order_payment_status = None

        create_order = Order.objects.create(
            user=current_user_profile,
            overall_price=overall_price,
            delivery_fee=delivery_fee,
            transaction_fee=transaction_fee,
            shipping=shipping,
            stores_infos=stores_infos,
            store_notes=store_notes,
            order_payment_status=order_payment_status,
            delivery_person_note=delivery_person_note,
        )
        create_order.linked_stores.set(available_stores)
        create_order.linked_items.set(available_items)
        create_order.save()

        return CreateOrderMutation(order=create_order, success=True)


class MarkOrderAsMutation(Output, graphene.Mutation):
    class Arguments:
        order_id = graphene.String(required=True)
        action = graphene.String(required=True)

    @permission_checker([IsAuthenticated])
    def mutate(self, info, order_id, action):
        user = info.context.user

        order = Order.objects.filter(order_track_id=order_id)

        if not order.exists():
            return MarkOrderAsMutation(error="Order does not exists")

        order = order.first()

        action = action.lower().replace("_", "-")
        allowed_actions = ["delivered", "ready-for-pickup"]

        if not action in allowed_actions:
            return MarkOrderAsMutation(error="Invalid action")
        if action == "delivered" and order.order_status != "out-for-delivery":
            return MarkOrderAsMutation(
                error="Order is not out for delivery, cannot be marked as delivered"
            )
        elif action == "ready-for-pickup" and order.order_status != "processing":
            return MarkOrderAsMutation(
                error="Order has not been processed, cannot be ready for pickup"
            )
        view_as = order.view_as(user.profile)

        if not "DELIVERY_PERSON" in view_as and not "VENDOR" in view_as:
            return MarkOrderAsMutation(
                error="You are not authorized to interact with this order"
            )
        current_delivery_person_id = user.profile.delivery_person.id
        delivery_person = order.get_delivery_person(current_delivery_person_id)

        if "DELIVERY_PERSON" in view_as and delivery_person is not None:
            order_delivery_people = order.delivery_people

            new_order_delivery_people_state = []
            all_delivered = True
            # update the current delivery person status
            for delivery_person in order_delivery_people:
                if delivery_person["id"] == current_delivery_person_id:
                    delivery_person["status"] = action
                # check if all delivery people have been delivered
                if delivery_person["status"] != "delivered":
                    all_delivered = False

                new_order_delivery_people_state.append(delivery_person)

            if all_delivered:
                order.order_status = "delivered"

            order.delivery_people = new_order_delivery_people_state

            # get delivery_fee by dividing the delivery fee by the number of delivery people
            delivery_fee = order.delivery_fee / len(order_delivery_people)

            delivery_person = user.profile.delivery_person

            # credit delivery person wallet
            credit_kwargs = {
                "amount": delivery_fee,
                "title": "Delivery Fee for Order #{}".format(
                    order.order_track_id.replace("order_", "")
                ),
                "order": order,
            }
            delivery_person.wallet.add_balance(**credit_kwargs)

            order.save()

            return MarkOrderAsMutation(success=True)

        elif "VENDOR" in view_as:
            order.order_status = "ready-for-pickup"
            order.save()
            order_disp_id = order.order_track_id.replace("order_", "")
            order.user.send_sms("Order #{} is ready for pickup".format(order_disp_id))

            return MarkOrderAsMutation(success=True)

        else:
            return MarkOrderAsMutation(
                error="You are not allowed to interact with this order"
            )


class RateItemMutation(graphene.Mutation):
    class Arguments:
        item_slug = graphene.String(required=True)
        rating = graphene.Argument(RatingInputType, required=True)

    success = graphene.Boolean()
    review_id = graphene.ID()

    @staticmethod
    @permission_checker([IsAuthenticated])
    def mutate(root, info, item_slug, rating):
        user = info.context.user
        try:
            item = Item.get_items().get(product_slug=item_slug)
            try:
                rating_qs = Rating.objects.get(user=user, item=item)
                rating_qs.stars = rating.stars.value
                rating_qs.comment = filter_comment(rating.comment)
                rating_qs.save()
                return RateItemMutation(success=True, review_id=rating_qs.id)
            except Rating.DoesNotExist:
                new_rating = Rating.objects.create(
                    user=user,
                    item=item,
                    stars=rating.stars.value,
                    comment=rating.comment,
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
            item = Item.get_items().get(product_slug=item_slug)
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
            response = order.create_payment_link()

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
