import graphene
from db.connection import execute_query

class LocationType(graphene.ObjectType):
    id = graphene.ID()
    country = graphene.String()
    state = graphene.String()
    latitude = graphene.Float()
    longitude = graphene.Float()

class Query(graphene.ObjectType):
    locations = graphene.List(LocationType)
    location = graphene.Field(LocationType, id=graphene.ID(required=True))

    def resolve_locations(self, info):
        query = "SELECT id, country, state, latitude, longitude FROM Locations"
        result = execute_query(query)
        return [LocationType(id=row[0], country=row[1], state=row[2], latitude=row[3], longitude=row[4]) for row in result]

    def resolve_location(self, info, id):
        query = "SELECT id, country, state, latitude, longitude FROM Locations WHERE id = %s"
        result = execute_query(query, (id,))
        if result:
            row = result[0]
            return LocationType(id=row[0], country=row[1], state=row[2], latitude=row[3], longitude=row[4])
        return None
