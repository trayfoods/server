import graphene
from ..types import ReviewType

class ReviewQueries(graphene.ObjectType):
    reviews = graphene.List(ReviewType, item_slug=graphene.String(required=True))

    def resolve_reviews(self, info, item_slug):
        from ..models import Rating
        return Rating.objects.filter(item__product_slug=item_slug)