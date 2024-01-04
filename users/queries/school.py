import graphene
from users.types import HostelType, HostelFieldType, SchoolType
from users.models import Hostel, School
from django.db.models import Q
from graphql import GraphQLError

class SchoolQueries(graphene.ObjectType):
    schools = graphene.List(
        SchoolType,
        name=graphene.String(required=False),
        country=graphene.String(required=False),
        count=graphene.Int(required=False),
    )

    school = graphene.Field(
        SchoolType,
        slug=graphene.String(required=True),
    )
    hostels = graphene.List(HostelType, school=graphene.String(required=True), gender=graphene.String(required=True), campus=graphene.String(required=False))

    hostel_fields = graphene.List(HostelFieldType, hostel=graphene.String(required=True))

    def resolve_hostels(self, info, school, gender, campus=None):
        gender = gender.upper()
        campus = campus.strip()
        return Hostel.objects.filter(school__slug=school, gender__name=gender, campus=campus).all()
    
    def resolve_hostel_fields(self, info, hostel):
        hostel = Hostel.objects.filter(slug=hostel).first()
        if hostel is None:
            raise GraphQLError("hostel does not exist")
        return hostel.fields.all()
    
    def resolve_schools(self, info, name=None, country=None, count=None):
        schools = []

        # check if country and name is not None
        if name and country:
            schools = School.objects.filter(
                Q(name__icontains=name) | Q(country__icontains=country)
            )

        if name is None and country is None:
            raise GraphQLError("name and country cannot be None")

        if name:
            schools = School.objects.filter(name__icontains=name)
        if country:
            schools = School.objects.filter(country__icontains=country)

        if count:
            schools = schools[:count]

        return schools

    def resolve_school(self, info, slug):
        school = School.objects.filter(slug=slug).first()
        if school is None:
            raise GraphQLError("school does not exist")
        return school