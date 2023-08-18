import hmac
import hashlib
import graphene
from django.utils.encoding import force_bytes
from django_countries import countries

from django.conf import settings
from core.types import IPInfoType, CountryType, UniversitySearchType

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


class CoreQueries(graphene.ObjectType):
    countries = graphene.List(CountryType)
    country = graphene.Field(CountryType, code=graphene.String())
    search_universities = graphene.List(
        UniversitySearchType, query=graphene.String(required=True), country=graphene.String()
    )
    ip_info = graphene.Field(IPInfoType)

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

    def resolve_search_universities(self, info, query, country=None):
        import universities

        uni = universities.API()
        if country:
            # county eg "Nigeria"
            return uni.search(country=country, name=query)
        return uni.search(name=query)

    def resolve_ip_info(self, info):
        from ipware import get_client_ip
        import requests

        ip, is_routable = get_client_ip(info.context)
        is_vpn = not is_routable

        # Get country information from ipinfo.io API
        country = None
        if ip:
            response = requests.get(f"https://ipinfo.io/{ip}/country")
            if response.status_code == 200:
                country = response.text.strip()

        return IPInfoType(ip_address=ip, is_vpn=is_vpn, country=country)


schema = graphene.Schema(query=CoreQueries, mutation=CoreMutations)
