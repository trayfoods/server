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

    class Meta:
        model = Item
        fields = ['product_name', 'id', 'product_clicks', 'product_views', 'product_qty', 'product_slug', 'product_calories', 'product_type', 'product_category', 'product_images', 'product_desc',
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
