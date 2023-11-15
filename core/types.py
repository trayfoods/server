import graphene


class CountryType(graphene.ObjectType):
    name = graphene.String(description="Country name")
    code = graphene.String(description="ISO 3166-1 alpha-2 country code")
    flag = graphene.String(description="URL to flag image")
    idd_code = graphene.String(description="International Direct Dialing code")

    def resolve_idd_code(self, info):
        return f"+{self.idd_code}"


class StateType(graphene.ObjectType):
    name = graphene.String(description="State name")
    code = graphene.String(description="ISO 3166-2 state code")
    


class IPInfoType(graphene.ObjectType):
    ip_address = graphene.String(description="User's IP address")
    is_vpn = graphene.Boolean(description="Whether the IP address is from a VPN")
    country = graphene.String(description="User's country based on IP address")


class UniversitySearchType(graphene.ObjectType):
    name = graphene.String()
    country = graphene.String()
    alpha_two_code = graphene.String()
    state_province = graphene.String()
    domains = graphene.List(graphene.String)
    web_pages = graphene.List(graphene.String)

class DeliveryType(graphene.ObjectType):
    name = graphene.String()
    fee = graphene.Decimal()
