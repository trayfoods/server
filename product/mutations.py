from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
from django.conf import settings
import graphene
from graphql import GraphQLError
from product.models import Item, ItemImage, ItemAttribute, Order, Rating, filter_comment
from product.types import ItemType
from users.models import UserActivity, Store, Profile, DeliveryPerson
from graphene_file_upload.scalars import Upload
from .types import (
    ShippingInputType,
    StoreNoteInputType,
    RatingInputType,
    StoreInfoInputType,
    StoreItemInputType,
)

from trayapp.permissions import IsAuthenticated, permission_checker


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
        product_categories = graphene.List(graphene.String)
        product_images = Upload(required=True)
        product_name = graphene.String(required=True)
        product_slug = graphene.String(required=True)
        product_type = graphene.String(required=True)
        product_price = graphene.Decimal(required=True)
        store_menu_name = graphene.String(required=True)
        product_share_visibility = graphene.String(required=True)

    product = graphene.Field(ItemType, default_value=None)

    @permission_checker([IsAuthenticated])
    def mutate(self, info, **kwargs):
        list_of_required_fields = [
            "product_slug",
            "product_name",
            "product_price",
            "product_type",
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
        product_categories_vals = kwargs.get("product_categories", None)
        product_type_val = kwargs.get("product_type")

        # Remove category, type and images from kwargs
        kwargs.pop("product_categories")
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
                product_categories = None
                if product_categories_vals and len(product_categories_vals) > 0:
                    product_categories = ItemAttribute.objects.filter(
                        slug__in=product_categories_vals
                    )
                product_type = ItemAttribute.objects.get(slug=product_type_val)

                if product is None and not profile is None:
                    # Spread the kwargs
                    save_data = {
                        **kwargs,
                        "product_creator": profile.store,
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
                        if not product_categories is None:
                            product.product_categories.set(product_categories)
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


class AddProductClickMutation(Output, graphene.Mutation):
    class Arguments:
        slug = graphene.String(required=True)

    def mutate(self, info, slug):
        item = (
            Item.get_items().filter(product_slug=slug, product_status="active").first()
        )
        if not item:
            return AddProductClickMutation(error="Item does not exist")

        product_creator: Store = item.product_creator
        if not product_creator:
            return AddProductClickMutation(error="Item does not have a creator")

        if not product_creator.is_open():
            return AddProductClickMutation(error="Item Store has closed")

        if info.context.user.is_authenticated:
            # Add the user activity
            new_activity = UserActivity.objects.create(
                user_id=info.context.user.id,
                activity_type="added_to_cart",
                item=item,
                timestamp=timezone.now(),
            )
            # increase the rank of the creator store by 0.5
            store = Store.objects.filter(id=item.product_creator.id).first()
            if not store is None:
                store.store_rank += 0.5
                store.save()
            # increase the product clicks by 1
            item.product_clicks += 1

            # save the changes
            item.save()
            new_activity.save()

            return AddProductClickMutation(success=True)
        else:
            return AddProductClickMutation(success=True)


class CreateOrderMutation(Output, graphene.Mutation):
    class Arguments:
        overall_price = graphene.Decimal(required=True)
        delivery_fee = graphene.Decimal(required=True)
        shipping = ShippingInputType(required=True)
        stores_infos = graphene.List(StoreInfoInputType, required=True)

        store_notes = graphene.List(StoreNoteInputType)
        delivery_person_note = graphene.String()
        extra_delivery_fee = graphene.Decimal()

    order_id = graphene.String()

    @permission_checker([IsAuthenticated])
    def mutate(
        self,
        info,
        stores_infos: list[StoreInfoInputType],
        **kwargs,
    ):
        overall_price = kwargs.get("overall_price", 0.00)
        delivery_fee = kwargs.get("delivery_fee", 0.00)
        shipping = kwargs.get("shipping")
        store_notes = kwargs.get("store_notes")
        delivery_person_note = kwargs.get("delivery_person_note")
        extra_delivery_fee = kwargs.get("extra_delivery_fee", 0.00)

        overall_price = Decimal(overall_price)
        delivery_fee = Decimal(delivery_fee)
        delivery_fee = delivery_fee.quantize(Decimal("1"), rounding=ROUND_HALF_UP)

        service_fee = Decimal(0.15) * overall_price
        service_fee = service_fee.quantize(Decimal("1"), rounding=ROUND_HALF_UP)

        # get all the items slugs and check if they exist
        avaliable_items: list[Item] = []
        for store_info in stores_infos:
            store_items: list[StoreItemInputType] = store_info.items
            for item in store_items:
                item_slug = item.product_slug
                item = (
                    Item.objects.filter(product_slug=item_slug, product_status="active")
                    .exclude(product_status="deleted")
                    .exclude(product_creator__is_approved=False)
                    .first()
                )
                if item is None:
                    raise GraphQLError(
                        "Order contains invalid items, clear cart and retry."
                    )
                avaliable_items.append(item)

        # check if there are linked items
        if len(avaliable_items) == 0:
            raise GraphQLError("Order contains no items")

        # get all the stores and check if they exist
        avaliable_stores: list[Store] = []
        for store_info in stores_infos:
            storeId = store_info.storeId
            store = Store.objects.filter(
                id=storeId,
            ).first()
            if store is None:
                raise GraphQLError(
                    f"Store with nickname '{storeId}' does not exist or is not approved"
                )
            if store.is_open() == False:
                raise GraphQLError(f"{store.store_name} has closed")
            if store.is_approved == False:
                raise GraphQLError(f"{store.store_name} has not been approved")
            if store.status != "online":
                raise GraphQLError(f"{store.store_name} is no longer taking orders")

            avaliable_stores.append(store)

        # check if there are linked stores
        if len(avaliable_stores) == 0:
            raise GraphQLError("Order contains no stores")

        # create status for each linked store
        stores_status = []
        for store in avaliable_stores:
            store_status = {
                "storeId": store.id,
                "status": "pending",
            }
            stores_status.append(store_status)

        new_stores_infos = []
        for store_info in stores_infos:
            new_stores_infos.append(
                {
                    "id": store_info.id,
                    "storeId": store_info.storeId,
                    "items": store_info.items,
                    "total": {
                        "price": store_info.total.price,
                        "plate_price": store_info.total.plate_price,
                    },
                    "count": {
                        "items": store_info.count.items,
                        "plate": store_info.count.plate,
                    },
                }
            )

        new_order = Order.objects.create(
            user=info.context.user.profile,
            overall_price=overall_price,
            delivery_fee=delivery_fee,
            service_fee=service_fee,
            shipping=shipping,
            store_notes=store_notes,
            stores_status=stores_status,
            delivery_person_note=delivery_person_note,
            extra_delivery_fee=extra_delivery_fee,
            stores_infos=new_stores_infos,
        )
        # set linked items and stores
        new_order.linked_items.set(avaliable_items)
        new_order.linked_stores.set(avaliable_stores)
        new_order.save()

        return CreateOrderMutation(order_id=new_order.order_track_id, success=True)

def get_store_name_from_store_status(current_order: Order):
    store_names = []
    for store in current_order.stores_status:
        store_id = store.get("storeId")
        store_qs = Store.objects.get(id=int(store_id))
        store_names.append(store_qs.store_name)

class MarkOrderAsMutation(Output, graphene.Mutation):
    class Arguments:
        order_id = graphene.String(required=True)
        action = graphene.String(required=True)

    success_msg = graphene.String()

    @permission_checker([IsAuthenticated])
    def mutate(self, info, order_id, action: str):
        user = info.context.user

        order = Order.objects.filter(order_track_id=order_id)

        if not order.exists():
            return MarkOrderAsMutation(error="Order does not exists")

        order = order.first()
        order.user: Profile = order.user
        shipping = order.shipping

        # check if the user has the right to interact with the order
        view_as = order.view_as(user.profile)
        # if not "DELIVERY_PERSON" in view_as and not "VENDOR" in view_as:
        #     return MarkOrderAsMutation(
        #         error="You are not authorized to interact with this order"
        #     )

        # convert action and order_status to lowercase and replace underscore with dash
        action = action.lower().replace("_", "-")
        order_status = order.get_order_status(user.profile).lower().replace("_", "-")

        # check if the action is allowed
        allowed_actions = settings.ALLOWED_STORE_ORDER_STATUS
        if not action in allowed_actions:
            return MarkOrderAsMutation(error="Invalid action")
        
        if "USER" in view_as or len(view_as) == 0:
            # check if the order user is the current user
            if order.user.user != user:
                return MarkOrderAsMutation(
                    error="You are not authorized to interact with this order"
                )
            
            if action == "cancelled":
                if order_status != "not-started" and not order.order_payment_status:
                    return MarkOrderAsMutation(
                        error="You cannot cancel this order because it has been marked as {}".format(
                            order_status.replace("-", " ").capitalize()
                        )
                    )
                order.order_status = "cancelled"
                order.save()
                return MarkOrderAsMutation(
                    success=True,
                    success_msg=f"Order {order.get_order_display_id()} has been cancelled",
                )

        # handle vendor actions
        if "VENDOR" in view_as:
            # TODO: check if the user is the vendor of the store

            # get the store id
            store_id = user.profile.store.id if user.profile.is_vendor else None
            if store_id is None:
                return MarkOrderAsMutation(error="You are not a vendor")

            store: Store = user.profile.store

            # check if the order has been accepted or rejected
            if order_status == "pending" and not action in ["accepted", "rejected"]:
                return MarkOrderAsMutation(
                    error="Order has not been accepted, cannot be marked as {}".format(
                        action.capitalize()
                    )
                )

            def get_store_statuses(current_order: Order, store_id: int, new_status):
                store_statuses = []
                for store_status in current_order.stores_status:
                    # remove the current store status and append the new status
                    if str(store_status["storeId"]) == str(store_id):
                        store_status["status"] = new_status
                    store_statuses.append(store_status["status"])
                return store_statuses

            # accept order if it is pending
            if action == "accepted":
                # calculate store balance
                stores_infos = order.stores_infos
                # find the current store info by store id
                current_store_info = None
                for store_info in stores_infos:
                    if str(store_info["storeId"]) == str(store_id):
                        current_store_info = store_info
                        break

                # check if the current store info was found
                if current_store_info is None:
                    return MarkOrderAsMutation(
                        error="No store info found for this order, please contact support"
                    )

                # get the store total normal price
                store_total_price = current_store_info["total"]["price"]
                # get the store plate price
                store_plate_price = current_store_info["total"]["plate_price"]

                overrall_store_price = Decimal(store_total_price) + Decimal(
                    store_plate_price
                )

                store_statuses = get_store_statuses(order, store_id, "accepted")

                # check if all stores has accepted the order
                if all(status == "accepted" for status in store_statuses):
                    # update the order status to accepted
                    order.order_status = "accepted"
                    order.save()

                    # notify the user that all stores has accepted the order
                    is_order_pickup = order.is_pickup()
                    has_notified_user = order.notify_user(
                        message=f"Order {order.get_order_display_id()} has been accepted, {"we will notify you when it's ready for pickup" if is_order_pickup else "we will notify you when it has been picked up by a delivery person"}",
                    )
                    if not has_notified_user:
                        return MarkOrderAsMutation(
                            error="An error occured while notifying customer, please try again later"
                        )

                # check if some stores has accepted the order
                elif any(status == "accepted" for status in store_statuses):
                    # update the order status to partially accepted
                    order.order_status = "partially-accepted"
                    order.save()

                    store_names = get_store_name_from_store_status(order)

                    store_names_with_comma = ", ".join(store_names)
                    # remove the last comma
                    store_names_with_comma = store_names_with_comma[:-2]

                    # notify the user that some stores has accepted the order
                    has_notified_user = order.notify_user(
                        message=f"Order {order.get_order_display_id()} has been accepted by {store_names_with_comma}, {"we will notify you when some are ready for pickup" if is_order_pickup else "we will notify you when some has been picked up by delivery people"}",
                    )

                # add the store total price to the store balance
                store.wallet.add_balance(
                    amount=overrall_store_price,
                    title="New Order Payment",
                    desc=f"Payment for Order {order.get_order_display_id()} was added to wallet",
                    order=order,
                )

                did_update = order.update_store_status(store_id, "accepted")

                if not did_update:
                    return MarkOrderAsMutation(
                        error="An error occured while updating order status, please try again later"
                    )

                return MarkOrderAsMutation(
                    success=True,
                    success_msg=f"Order {order.get_order_display_id()} has been accepted",
                )

            # reject order if it is pending
            if action == "rejected":
                store_statuses = get_store_statuses(order, store_id, "rejected")

                # check if all stores has rejected the order
                if all(status == "rejected" for status in store_statuses):
                    # update the order status to rejected
                    order.order_status = "rejected"
                    order.save()

                    # notify the user that all stores has rejected the order
                    has_notified_user = order.notify_user(
                        message=f"Order {order.get_order_display_id()} has been rejected",
                    )

                # check if some stores has rejected the order
                elif any(status == "rejected" for status in store_statuses):
                    # update the order status to partially rejected
                    order.order_status = "partially-rejected"
                    order.save()
                    # get the stores names that rejected the order
                    store_names = get_store_name_from_store_status(order)

                    store_names_with_comma = ", ".join(store_names)
                    # remove the last comma
                    store_names_with_comma = store_names_with_comma[:-2]

                    # notify the user that some stores has rejected the order
                    order.notify_user(
                        message=f"The items from your order {order.get_order_display_id()} provided by {store_names_with_comma} have been rejected.",
                    )

                did_update = order.update_store_status(store_id, "rejected")
                if not did_update:
                    return MarkOrderAsMutation(
                        error="An error occured while updating order status, please try again later"
                    )

                # refund funds from each store that has rejected the order
                for store_status in order.stores_status:
                    if store_status["status"] == "rejected":
                        # get the store id
                        store_id = store_status.get("storeId", None)

                        if store_id is None:
                            return MarkOrderAsMutation(
                                error="No store id found for this order, please contact support"
                            )

                        # refund the customer
                        order.store_refund_customer(store_id)

                return MarkOrderAsMutation(
                    success=True,
                    success_msg=f"Order {order.get_order_display_id()} has been rejected",
                )

            # handle order cancelled
            if action == "cancelled":
                if order_status != "accepted":
                    return MarkOrderAsMutation(
                        error="You cannot cancel this order because it has been marked as {}".format(
                            order_status.replace("-", " ").capitalize()
                        )
                    )

                store_statuses = get_store_statuses(order, store_id, "cancelled")
                # check if all stores has cancelled the order
                if all(status == "cancelled" for status in store_statuses):
                    # update the order status to cancelled
                    order.order_status = "cancelled"
                    order.save()

                    # notify the user that all stores has cancelled the order
                    has_notified_user = order.notify_user(
                        message=f"Order {order.get_order_display_id()} has been cancelled",
                    )
                    if not has_notified_user:
                        return MarkOrderAsMutation(
                            error="An error occured while notifying customer, please try again later"
                        )

                # check if some stores has cancelled the order
                elif any(status == "cancelled" for status in store_statuses):
                    # update the order status to partially cancelled
                    order.order_status = "partially-cancelled"
                    order.save()

                    # get the stores names that cancelled the order
                    store_names = get_store_name_from_store_status(order)

                    store_names_with_comma = ", ".join(store_names)
                    # remove the last comma
                    store_names_with_comma = store_names_with_comma[:-2]

                    # notify the user that some stores has cancelled the order
                    order.notify_user(
                        message=f"The items from your Order {order.get_order_display_id()} provided by {store_names_with_comma} have been cancelled.",
                    )

                did_update = order.update_store_status(store_id, "cancelled")
                if not did_update:
                    return MarkOrderAsMutation(
                        error="An error occured while updating order status, please try again later"
                    )

                # refund funds from each store that has cancelled the order
                for store_status in order.stores_status:
                    if store_status["status"] == "cancelled":
                        # get the store id
                        store_id = store_status.get("storeId", None)

                        if store_id is None:
                            return MarkOrderAsMutation(
                                error="No store id found for this order, please contact support"
                            )

                        # refund the customer
                        order.store_refund_customer(store_id)

                return MarkOrderAsMutation(success=True, success_msg="Order cancelled")

            # handle order ready for delivery
            if action == "ready-for-delivery":
                if shipping and shipping["address"] == "pickup":
                    return MarkOrderAsMutation(
                        error="Order address is pickup, cannot be marked as ready for delivery"
                    )
                # check if the order has not been accepted
                if order_status != "accepted":
                    return MarkOrderAsMutation(
                        error="Order has not been accepted, cannot be marked as ready for delivery"
                    )

                # handle order ready for delivery
                delivery_people = DeliveryPerson.get_delivery_people_that_can_deliver(
                    order
                )
                # check if any delivery person was found
                if len(delivery_people) == 0:
                    return MarkOrderAsMutation(
                        error="No delivery person found for this order"
                    )
                has_sent_notifications = order.notify_delivery_people(
                    delivery_people, store_id
                )
                if not has_sent_notifications:
                    return MarkOrderAsMutation(
                        error="An error occured while notifying delivery people, please try again later"
                    )
                store_statuses = get_store_statuses(order, store_id, "ready-for-delivery")

                # check if all stores has marked the order as ready for delivery
                if all(status == "ready-for-delivery" for status in store_statuses):
                    # update the order status to ready for delivery
                    order.order_status = "ready-for-delivery"
                    order.save()
                    
                elif any(status == "ready-for-delivery" for status in store_statuses):
                    # update the order status to partially ready for delivery
                    order.order_status = "partially-ready-for-delivery"
                    order.save()

                did_update = order.update_store_status(store_id, "ready-for-delivery")
                if not did_update:
                    return MarkOrderAsMutation(
                        error="An error occured while updating order status, please try again later"
                    )
                return MarkOrderAsMutation(
                    success=True,
                    success_msg=f"Order {order.get_order_display_id()} has been marked as ready for delivery",
                )

            # handle order ready for pickup
            if action == "ready-for-pickup":
                if shipping and shipping["address"] != "pickup":
                    return MarkOrderAsMutation(
                        error="Order address is not pickup, cannot be marked as ready for pickup"
                    )
                # check if the order has not been accepted
                if order_status != "accepted":
                    return MarkOrderAsMutation(
                        error="Order has not been accepted, cannot be marked as ready for pickup"
                    )

                store_statuses = get_store_statuses(order, store_id, "ready-for-pickup")

                # check if all stores has marked the order as ready for pickup
                if all(status == "ready-for-pickup" for status in store_statuses):
                    # update the order status to ready for pickup
                    order.order_status = "ready-for-pickup"
                    order.save()

                    # notify the user that all stores has marked the order as ready for pickup
                    has_notified_user = order.notify_user(
                        message=f"Order {order.get_order_display_id()} is ready for pickup",
                    )
                    if not has_notified_user:
                        return MarkOrderAsMutation(
                            error="An error occured while notifying customer, please try again later"
                        )

                # check if some stores has marked the order as ready for pickup
                elif any(status == "ready-for-pickup" for status in store_statuses):
                    # update the order status to partially ready for pickup
                    order.order_status = "partially-ready-for-pickup"
                    order.save()

                    # get the stores names that marked the order as ready for pickup
                    store_names = get_store_name_from_store_status(order)

                    store_names_with_comma = ", ".join(store_names)
                    # remove the last comma
                    store_names_with_comma = store_names_with_comma[:-2]

                    # notify the user that some stores has marked the order as ready for pickup
                    has_notified_user = order.notify_user(
                        message=f"Some items from your order {order.get_order_display_id()} are now ready for pickup.",
                    )

                did_update = order.update_store_status(store_id, "ready-for-pickup")
                if not did_update:
                    return MarkOrderAsMutation(
                        error="An error occured while updating order status, please try again later"
                    )

                return MarkOrderAsMutation(
                    success=True,
                    success_msg=f"Order {order.get_order_display_id()} has been marked as ready for pickup",
                )

            # handle order picked up
            if action == "picked-up":
                if shipping and shipping["address"] == "pickup":
                    # check if the order has not been marked as ready for pickup
                    if order_status != "ready-for-pickup":
                        return MarkOrderAsMutation(
                            error="Order has not been marked as ready for pickup, cannot be marked as picked up"
                        )

                    # notify the user that the order has been picked up
                    order.user.send_sms(
                        message=f"Your Order {order.get_order_display_id()} has been picked up"
                    )
                    did_update = order.update_store_status(store_id, "picked-up")
                    if not did_update:
                        return MarkOrderAsMutation(
                            error="An error occured while updating order status, please try again later"
                        )

                    return MarkOrderAsMutation(
                        success=True,
                        success_msg=f"Order {order.get_order_display_id()} has been marked as picked up",
                    )
                else:
                    # check if the order has not been marked as ready for delivery
                    if order_status != "ready-for-delivery":
                        return MarkOrderAsMutation(
                            error="The order hasn't been marked as ready for delivery yet, so it can't be marked as picked up."
                        )

                    # get the delivery person full name and phone number
                    delivery_person = order.get_delivery_person(store_id=store_id)
                    if not delivery_person:
                        return MarkOrderAsMutation(
                            error="Hmm, we couldn't find a delivery person for this order. Please try again later."
                        )

                    delivery_person_qs = DeliveryPerson.objects.filter(
                        id=delivery_person["id"]
                    )

                    if not delivery_person_qs.exists():
                        return MarkOrderAsMutation(
                            error="we couldn't find a delivery person for this order. Please try again later."
                        )

                    delivery_person = delivery_person_qs.first()

                    # update the store status to out for delivery
                    did_update = order.update_store_status(store_id, "out-for-delivery")

                    if not did_update:
                        return MarkOrderAsMutation(
                            error="Sorry, there was an issue updating the order status. Could you please try again later?"
                        )
                    
                    # update the delivery person status to picked up
                    did_update = order.update_delivery_person_status(
                        store_id=store_id, status="out-for-delivery"
                    )

                    if not did_update:
                        return MarkOrderAsMutation(
                            error="Sorry, there was an issue updating the order status. Could you please try again later?r"
                        )
                    

                    # notify the user that the order has been picked up
                    order.notify_user(
                        message=f"Your order {order.get_order_display_id()} from {store.store_name} has been picked up by {delivery_person.profile.user.get_full_name()}. We'll keep you updated on delivery progress. Your order is now on its way!"
                    )

                    return MarkOrderAsMutation(
                        success=True,
                        success_msg=f"Order {order.get_order_display_id()} has been marked as out for delivery",
                    )

        # TODO: handle delivery person actions
        if "DELIVERY_PERSON" in view_as:
            current_delivery_person = user.profile.get_delivery_person()
            if current_delivery_person is None:
                return MarkOrderAsMutation(error="You are not a delivery person")
            current_delivery_person_id = current_delivery_person.id
            delivery_person = order.get_delivery_person(
                delivery_person_id=current_delivery_person_id
            )

            if delivery_person is not None:
                delivery_person_store_id = delivery_person.get("storeId", None)
                if delivery_person_store_id is None:
                    return MarkOrderAsMutation(
                        error="No store id found for this order, please contact support"
                    )
                order_delivery_people = order.delivery_people

                did_update = order.update_delivery_person_status(
                    delivery_person_id=current_delivery_person_id, status="delivered"
                )

                if not did_update:
                    return MarkOrderAsMutation(
                        error="An error occured while updating order delivery status, please try again later"
                    )

                # update store status that the delivery person has delivered the order
                did_update = order.update_store_status(
                    delivery_person_store_id, "delivered"
                )
                if not did_update:
                    return MarkOrderAsMutation(
                        error="An error occured while updating order status, please try again later"
                    )

                # get delivery_fee by dividing the delivery fee by the number of delivery people
                delivery_fee = order.delivery_fee / len(order_delivery_people)

                delivery_person: DeliveryPerson = user.profile.get_delivery_person()

                # credit delivery person wallet
                credit_kwargs = {
                    "amount": delivery_fee,
                    "title": "Delivery Fee",
                    "desc": f"Delivery Fee for Order {order.get_order_display_id()}",
                    "order": order,
                }
                delivery_person.wallet.add_balance(**credit_kwargs)

                order.save()

                delivery_people_statuses = []
                for delivery_person in order.delivery_people:
                    delivery_people_statuses.append(delivery_person["status"])

                # check if all delivery people has delivered the order
                if all(status == "delivered" for status in delivery_people_statuses):
                    # update the order status to delivered
                    order.order_status = "delivered"
                    order.save()

                # check if some delivery people has delivered the order
                elif any(status == "delivered" for status in delivery_people_statuses):
                    # update the order status to partially delivered
                    order.order_status = "partially-delivered"
                    order.save()

                return MarkOrderAsMutation(success=True)


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

                # update order payment status to pending
                order.order_payment_status = "pending"
                order.save()

                return InitializeTransactionMutation(
                    success=True, transaction_id=transaction_id, payment_url=payment_url
                )
            else:
                raise GraphQLError(response["message"])
        except Exception as e:
            print(e)
            raise GraphQLError("An error occured while initializing transaction")
