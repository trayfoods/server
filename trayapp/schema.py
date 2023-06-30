import users.schema
import product.schema
import graphene
from django.conf import settings

APP_VERSION = settings.APP_VERSION

class Query(users.schema.Query, product.schema.Query, graphene.ObjectType):
    app_version = graphene.String()

    def resolve_app_version(self, info):
        return APP_VERSION

class Mutation(users.schema.Mutation, product.schema.Mutation, graphene.ObjectType):
    pass

schema = graphene.Schema(query=Query, mutation=Mutation)