import graphene
from db.connection import execute_query

class ProductType(graphene.ObjectType):
    id = graphene.ID()
    name = graphene.String()
    category = graphene.String()
    subCategory = graphene.String()  # Corrigido para camelCase
    unitCost = graphene.Float()      # Corrigido para camelCase
    unitPrice = graphene.Float()     # Corrigido para camelCase

class Query(graphene.ObjectType):
    products = graphene.List(ProductType)
    product = graphene.Field(ProductType, id=graphene.ID(required=True))

    def resolve_products(self, info):
        query = """
            SELECT id, name, category, sub_category, unit_cost, unit_price
            FROM Products
        """
        result = execute_query(query)
        return [
            ProductType(
                id=row[0],
                name=row[1],
                category=row[2],
                subCategory=row[3],  # Mapear sub_category para subCategory
                unitCost=row[4],     # Mapear unit_cost para unitCost
                unitPrice=row[5]     # Mapear unit_price para unitPrice
            )
            for row in result
        ]

    def resolve_product(self, info, id):
        query = """
            SELECT id, name, category, sub_category, unit_cost, unit_price
            FROM Products WHERE id = %s
        """
        result = execute_query(query, (id,))
        if result:
            row = result[0]
            return ProductType(
                id=row[0],
                name=row[1],
                category=row[2],
                subCategory=row[3],  # Mapear sub_category para subCategory
                unitCost=row[4],     # Mapear unit_cost para unitCost
                unitPrice=row[5]     # Mapear unit_price para unitPrice
            )
        return None
