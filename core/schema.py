import hmac
import hashlib
import graphene
from django.utils.encoding import force_bytes
from django_countries import countries

from django.conf import settings

STATIC_URL = settings.STATIC_URL


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


class CountryType(graphene.ObjectType):
    name = graphene.String()
    code = graphene.String()
    flag = graphene.String()


class CoreQueries(graphene.ObjectType):
    countries = graphene.List(CountryType)
    country = graphene.Field(CountryType, code=graphene.String())

    def resolve_countries(self, info):
        return [
            CountryType(
                name=name,
                code=code,
                flag=info.context.build_absolute_uri(
                    f"{STATIC_URL}/flags/{code.lower()}.gif".replace("//", "/")
                ),
            )
            for code, name in list(countries)
        ]

    def resolve_country(self, info, code):
        code = code.upper()
        name = dict(countries).get(code)
        if name is None:
            return None
        return CountryType(
            name=name,
            code=code.upper(),
            flag=info.context.build_absolute_uri(
                f"{STATIC_URL}/flags/{code.lower()}.gif".replace("//", "/")
            ),
        )


schema = graphene.Schema(query=CoreQueries, mutation=CoreMutations)
