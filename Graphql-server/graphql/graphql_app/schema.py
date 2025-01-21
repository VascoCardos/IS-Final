import graphene
from graphql_app.resolvers.Location import Query as LocationQuery
from graphql_app.resolvers.Product import Query as ProductQuery
from graphql_app.resolvers.Sale import Query as SaleQuery

class Query(LocationQuery, ProductQuery, SaleQuery, graphene.ObjectType):
    pass

schema = graphene.Schema(query=Query)
