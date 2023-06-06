import graphene
from graphql import GraphQLError
from product.types import ItemType, ItemAttributeType
from product.mutations import (AddAvaliableProductMutation,
                               AddMultipleAvaliableProductsMutation, AddProductMutation, 
                               AddProductClickMutation, CreateOrderMutation, RateItemMutation, HelpfulReviewMutation)
from product.models import Item, ItemAttribute
from product.utils import recommend_items
from users.models import UserActivity
from trayapp.custom_model import ItemsAvalibilityNode
from django.utils import timezone
# basic searching
from django.db.models import Q
# from io import BytesIO
# from PIL import Image
# import cv2
# import numpy as np
# import base64
# from graphene.types.scalars import String

class Query(graphene.ObjectType):
    # remove_background = graphene.Field(
    #     String,
    #     image_b64=graphene.String(required=True),
    #     description="Remove the background from an image"
    # )
    hero_data = graphene.List(ItemType, count=graphene.Int(required=False))
    items = graphene.List(ItemType, count=graphene.Int(required=True))
    item = graphene.Field(ItemType, item_slug=graphene.String())

    item_attributes = graphene.List(ItemAttributeType, _type=graphene.Int())
    item_attribute = graphene.Field(
        ItemAttributeType, urlParamName=graphene.String())

    search_items = graphene.List(ItemType, query=graphene.String(
        required=True), count=graphene.Int(required=False))

    check_muliple_items_is_avaliable = graphene.List(
        ItemsAvalibilityNode, items_slug_store_nickName=graphene.String(required=True))

    def resolve_check_muliple_items_is_avaliable(self, info, items_slug_store_nickName):
        list_of_items = []
        if items_slug_store_nickName.find(">") > -1 and items_slug_store_nickName.find(",") > -1:
            list_of_items_str = items_slug_store_nickName.split(",")
            if list_of_items_str:
                for item_str in list_of_items_str:
                    if item_str != "":
                        item_slug, store_nickName = item_str.split(">")
                        item = Item.objects.filter(
                            product_slug=item_slug).first()
                        if not item is None:
                            new_item = {
                                "product_slug": item.product_slug,
                                "store_avaliable_in": item.product_avaliable_in.all(),
                                "is_avaliable": False,
                                "avaliable_store": store_nickName
                            }
                            store_checker = item.product_avaliable_in.filter(
                                store_nickname=store_nickName).first()
                            if store_checker:
                                new_item = {
                                    "product_slug": item.product_slug,
                                    "store_avaliable_in": item.product_avaliable_in.all(),
                                    "is_avaliable": True,
                                    "avaliable_store": store_checker.store_nickname
                                }
                            list_of_items.append(new_item)
        return list_of_items

    def resolve_search_items(self, info, query, count=None):
        filtered_items = Item.objects.filter(Q(product_name__icontains=query) | Q(
            product_desc__icontains=query) | Q(product_slug__iexact=query))
        if count:
            count = count + 1
            if filtered_items.count() >= count:
                filtered_items = filtered_items[:count]
        else:
            filtered_items = filtered_items[:20]
        return filtered_items

    def resolve_hero_data(self, info, count=None):
        items = Item.objects.filter(product_type__urlParamName__icontains="dish").exclude(
            product_type__urlParamName__icontains="not").order_by("-product_clicks")
        if count:
            count = count + 1
            if items.count() >= count:
                items = items[:count]
        return items

    def resolve_items(self, info, count):
        if count:
            count = count + 1
            items = Item.objects.all().distinct()
            items = items[:count if items.count() >= count else items.count()]
            # try:
            #     if info.context.user.is_authenticated and UserActivity.objects.filter(user_id=info.context.user.id).count() > 2:
            #         return recommend_items(info.context.user.id, n=count if (items.count() >= count) else items.count())
            #     else:
            #         return items
            # except:
            return items
        else:
            GraphQLError("There should be a count param in the items query")

    def resolve_item(self, info, item_slug):
        item = Item.objects.filter(product_slug=item_slug).first()
        if not item is None:
            item.product_views += 1
            item.save()
            if info.context.user.is_authenticated:
                new_activity = UserActivity.objects.create(
                    user_id=info.context.user.id,
                    activity_message=None,
                    activity_type="view", item=item, timestamp=timezone.now())
                new_activity.save()
        else:
            raise GraphQLError("404: Item Not Found")
        return item

    def resolve_all_item_attributes(self, info, **kwargs):
        return ItemAttribute.objects.all()

    def resolve_item_attributes(self, info, _type):
        if _type == 0:
            _type = "TYPE"
        elif _type == 1:
            _type = "CATEGORY"
        else:
            raise GraphQLError(
                "Please enter either 0 or 1 for types and categories respectively")
        item_attributes = ItemAttribute.objects.filter(_type=_type)
        return item_attributes

    def resolve_item_attribute(self, info, urlParamName):
        item_attribute = ItemAttribute.objects.filter(
            urlParamName=urlParamName).first()
        return item_attribute

    # def resolve_remove_background(self, info, image_b64):
    #     # Decode the base64 encoded image to a numpy array
    #     img_data = base64.b64decode(image_b64)
    #     img_array = np.frombuffer(img_data, np.uint8)
    #     img = cv2.imdecode(img_array, cv2.IMREAD_UNCHANGED)

    #     # Convert the image to grayscale and adjust the contrast
    #     gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    #     clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    #     gray = clahe.apply(gray)

    #     # Apply edge detection to find the contours of the object
    #     edges = cv2.Canny(gray, 50, 150)

    #     # Dilate the edges to close any gaps in the object
    #     kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    #     edges = cv2.dilate(edges, kernel, iterations=1)

    #     # Find the contours of the object and select the largest one
    #     contours, hierarchy = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    #     contour_sizes = [(cv2.contourArea(contour), contour) for contour in contours]
    #     if contour_sizes:
    #         largest_contour = max(contour_sizes, key=lambda x: x[0])[1]
    #     else:
    #         largest_contour = None

    #     # Create a mask from the largest contour
    #     mask = np.zeros(edges.shape, dtype=np.uint8)
    #     if largest_contour is not None:
    #         cv2.drawContours(mask, [largest_contour], -1, 255, -1)

    #     # Apply the mask to the original image to remove the background
    #     result = cv2.bitwise_and(img, img, mask=mask)

    #     # Convert the resulting image to PIL Image format
    #     result_pil = Image.fromarray(result)

    #     # Convert the PIL Image to base64 encoding
    #     buffered = BytesIO()
    #     result_pil.save(buffered, format="PNG")
    #     result_base64 = base64.b64encode(buffered.getvalue()).decode()

    #     return result_base64
    
class Mutation(graphene.ObjectType):
    add_product = AddProductMutation.Field()
    add_product_click = AddProductClickMutation.Field()
    add_available_product = AddAvaliableProductMutation.Field()
    add_available_products = AddMultipleAvaliableProductsMutation.Field()
    create_order = CreateOrderMutation.Field()
    rate_item = RateItemMutation.Field()
    helpful_review = HelpfulReviewMutation.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)
