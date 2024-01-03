import graphene

class HostelFieldInput(graphene.InputObjectType):
    field_id = graphene.String()
    value = graphene.String()