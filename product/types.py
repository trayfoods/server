import graphene
from graphene_django.types import DjangoObjectType
from pkg_resources import require
from .models import Item, ItemAttribute, ItemImage
from users.models import Vendor, Store


class ItemImageType(DjangoObjectType):
    product_image = graphene.String()
    product_image_webp = graphene.String()

    class Meta:
        model = ItemImage
        fields = ['id', 'product_image', 'product_image_webp', 'is_primary']

    def resolve_product_image(self, info, *args, **kwargs):
        product_image = info.context.build_absolute_uri(self.item_image.url)
        return product_image

    def resolve_product_image_webp(self, info, *args, **kwargs):
        product_image_webp = info.context.build_absolute_uri(
            self.item_image_webp.url)
        return product_image_webp


class ItemAttributeType(DjangoObjectType):
    class Meta:
        model = ItemAttribute
        fields = '__all__'


class ItemType(DjangoObjectType):
    id = graphene.Int(storeNickname=graphene.String(required=False))
    product_images = graphene.List(
        ItemImageType, count=graphene.Int(required=False))
    is_avaliable = graphene.Boolean()
    has_qty = graphene.Boolean()
    is_avaliable_for_store = graphene.String()
    avaliable_store = graphene.String(storeNickname=graphene.String(required=False))

    class Meta:
        model = Item
        fields = ['product_name', 'id', 'avaliable_store', 'is_avaliable_for_store', 'product_clicks', 'product_views', 'product_qty', 'product_slug', 'product_calories', 'product_type', 'product_category', 'product_images', 'product_desc',
                  'product_price', 'product_avaliable_in', 'has_qty', 'product_creator', 'product_created_on', 'is_avaliable']

    # This will add a unqiue id, if the store items are the same
    def resolve_id(self, info, storeNickname=None):
        item_id = self.id
        if storeNickname:
            storeName = Store.objects.filter(store_nickname=storeNickname).first()
            if not storeName is None:
                item_id = self.id + storeName.id
        return item_id

    def resolve_product_qty(self, info):
        product_qty = self.product_qty
        if product_qty == 0:
            product_qty = 1
        return product_qty

    def resolve_has_qty(self, info):
        has_qty = False
        if self.product_qty > 0:
            has_qty = True
        return has_qty

    def resolve_is_avaliable_for_store(self, info):
        user = info.context.user
        store_item = "not_login"
        if user.is_authenticated:
            store_item = "not_vendor"
            vendor = Vendor.objects.filter(user=user.profile).first()
            if not vendor is None:
                is_product_in_store = vendor.store.store_products.filter(
                    product_slug=self.product_slug).first()
                if not is_product_in_store is None:
                    store_item = "1"
                else:
                    store_item = "0"
        return store_item

    def resolve_product_images(self, info, count=None):
        images = ItemImage.objects.filter(product=self)
        if self.product_images.count() == images.count():
            images = images
        else:
            images = self.product_images.all()

        if not count == None:
            count = count + 1
            if images.count() >= count:
                images = images[:count]
                if images is None:
                    images = self.product_images.all()

        return images

    def resolve_is_avaliable(self, info):
        if len(self.product_avaliable_in.all()) > 0:
            is_avaliable = True
        else:
            is_avaliable = False
        return is_avaliable

    def resolve_avaliable_store(self, info, storeNickname=None):
        store_nickname = None
        if storeNickname:
            store_nickname = Store.objects.filter(store_nickname=storeNickname).first()
            if not store_nickname is None:
                store_nickname = store_nickname.store_nickname
        if store_nickname == None:
            is_avaliable = len(self.product_avaliable_in.all()) > 0
            if self.product_creator is None:
                if is_avaliable:
                    store_nickname = self.product_avaliable_in.first().store_nickname
            else:
                isStore = False
                store = self.product_avaliable_in.filter(
                    store_nickname=self.product_creator.store.store_nickname).first()
                if not store is None:
                    isStore = True
                if isStore == True:
                    store_nickname = self.product_creator.store.store_nickname
                else:
                    if is_avaliable:
                        store_nickname = self.product_avaliable_in.first().store_nickname
        return store_nickname
