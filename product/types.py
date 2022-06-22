import graphene
from graphene_django.types import DjangoObjectType
from .models import Item, ItemAttribute, ItemImage


class ItemImageType(DjangoObjectType):
    product_image = graphene.String()

    class Meta:
        model = ItemImage
        fields = ['product_image', 'is_primary']

    def resolve_product_image(self, info, *args, **kwargs):
        product_image = info.context.build_absolute_uri(self.item_image.url)
        return product_image


class ItemAttributeType(DjangoObjectType):
    class Meta:
        model = ItemAttribute
        fields = '__all__'


class ItemType(DjangoObjectType):
    product_images = graphene.List(
        ItemImageType, count=graphene.Int(required=False))
    is_avaliable = graphene.Boolean()
    avaliable_store = graphene.String()

    class Meta:
        model = Item
        fields = ['product_name', 'id', 'avaliable_store', 'product_clicks', 'product_views', 'product_qty', 'product_slug', 'product_calories', 'product_type', 'product_category', 'product_images', 'product_desc',
                  'product_price', 'product_avaliable_in', 'product_creator', 'product_created_on', 'is_avaliable']

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


#   const searchStoreNickName = (item) => {
#     let store_Nickname = null;
#     if (item?.productCreator === null) {
#       store_Nickname = item?.productAvaliableIn[0].storeNickname;
#     } else {
#       let data = item?.productAvaliableIn.filter(
#         (n) =>
#           n.storeNickname ===
#           item.productCreator.profile.vendor.store?.storeNickname
#       );
#       store_Nickname =
#         data && data.length > 0
#           ? data[0].storeNickname
#           : item?.productAvaliableIn[0].storeNickname;
#     }
#     return item?.productAvaliableIn && item?.productAvaliableIn.length > 0
#       ? store_Nickname
#       : null;
#   };

    def resolve_avaliable_store(self, info):
        store_nickname = None
        if self.product_creator is None:
            if len(self.product_avaliable_in.all()) > 0:
                store_nickname = self.product_avaliable_in.first().store_nickname
        else:
            isStore = False
            for store in self.product_avaliable_in.all():
                if store.store_nickname == self.product_creator.store.store_nickname:
                    isStore = True
            if isStore == True:
                store_nickname = self.product_creator.store.store_nickname
            else:
                if len(self.product_avaliable_in.all()) > 0:
                    store_nickname = self.product_avaliable_in.first().store_nickname
        return store_nickname
