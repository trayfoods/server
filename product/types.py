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

    class Meta:
        model = Item
        fields = ['product_name', 'product_slug', 'product_calories', 'product_type', 'product_category', 'product_images', 'product_desc',
                  'product_price', 'product_avaliable_in', 'product_creator', 'product_created_on']

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
