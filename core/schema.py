import hmac
import hashlib
import graphene
from django.utils.encoding import force_bytes


class HashGeneratorMutation(graphene.Mutation):
    class Arguments:
        string = graphene.String(required=True)
        type = graphene.String(required=True)

    hash = graphene.String()
    success = graphene.Boolean(default_value=False)

    def mutate(self, info, string, type):
        list_of_types = ["notify", "pin"]
        if type not in list_of_types:
            raise Exception("Invalid Hash Type")

        # sha512 hash
        hash = hmac.new(
            key=force_bytes(string),
            msg=force_bytes(type),
            digestmod=hashlib.sha512,
        ).hexdigest()
        return HashGeneratorMutation(hash=hash, success=True)




class CoreMutations(graphene.ObjectType):
    generate_hash = HashGeneratorMutation.Field()

class CoreQueries(graphene.ObjectType):
    pass