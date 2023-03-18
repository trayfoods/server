import users.schema
import product.schema
import graphene

class Query(users.schema.Query, product.schema.Query, graphene.ObjectType):
    pass

class Mutation(users.schema.Mutation, product.schema.Mutation, graphene.ObjectType):
    pass

schema = graphene.Schema(query=Query, mutation=Mutation)