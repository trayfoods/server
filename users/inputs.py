import graphene

class StudentHostelFieldInput(graphene.InputObjectType):
    field_id = graphene.String()
    value = graphene.String()