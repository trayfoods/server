import graphene
from graphene_django.filter import DjangoFilterConnectionField
from ..models import Rating
from ..types import ReviewNode


class ReviewsQueries(graphene.ObjectType):
    reviews = DjangoFilterConnectionField(
        ReviewNode, item_slug=graphene.String(required=True)
    )

    def resolve_reviews(self, info, item_slug, **kwargs):
        return Rating.objects.filter(item__product_slug=item_slug)
