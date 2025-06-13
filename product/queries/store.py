import graphene
from django.db.models import Q
# from django.contrib.gis.geos import Point
# from django.contrib.gis.measure import D
from users.models import Store
from product.models import Item
from product.types import StoreType


class StoreQueries(graphene.ObjectType):
    nearby_stores = graphene.List(
        StoreType,
        latitude=graphene.Float(required=True),
        longitude=graphene.Float(required=True),
        radius=graphene.Float(required=True),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    def resolve_nearby_stores(
        self, info, latitude, longitude, radius, limit=None, offset=0
    ):
        # Convert radius from kilometers to meters
        radius_meters = radius * 1000

        # Create a point from the given coordinates
        # user_location = Point(longitude, latitude, srid=4326)

        # Base query for stores within radius
        stores_query = (
            Store.objects.filter(
                Q(primary_address_lat__isnull=False)
                & Q(primary_address_lng__isnull=False)
                & Q(is_approved=True)
                & Q(status="online")
            )
            # .filter(location__distance_lte=(user_location, D(m=radius_meters)))
            .select_related(
                "vendor", "vendor__user", "store_type", "gender_preference", "school"
            )
            .prefetch_related(
                "menus",
                "menus__items",
                "menus__items__product_images",
                "storeopenhours_set",
            )
        )

        # Apply pagination if specified
        if limit is not None:
            stores_query = stores_query[offset : offset + limit]

        # Execute query and calculate distances
        stores = list(stores_query)

        # Calculate distance and is_open status for each store
        for store in stores:
            # store_location = Point(
            #     store.primary_address_lng, store.primary_address_lat, srid=4326
            # )
            # store.distance = (
            #     user_location.distance(store_location) / 1000
            # )  # Convert to kilometers

            # Add is_open_data to store
            is_open_data = store.get_is_open_data()
            store.is_open_data = {
                "is_open": is_open_data["is_open"],
                "message": is_open_data["message"],
            }

        # Sort by distance and store rank
        # stores.sort(key=lambda x: (x.distance, -x.store_rank))

        return stores
