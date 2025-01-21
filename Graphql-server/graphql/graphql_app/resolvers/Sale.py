import graphene
from db.connection import execute_query


class SaleType(graphene.ObjectType):
    id = graphene.ID()
    saleDate = graphene.String()
    customerAge = graphene.Int()
    customerGender = graphene.String()
    orderQuantity = graphene.Int()
    profit = graphene.Float()
    cost = graphene.Float()
    revenue = graphene.Float()

class Query(graphene.ObjectType):
    sales = graphene.List(SaleType)
    sale = graphene.Field(SaleType, id=graphene.ID(required=True))

    def resolve_sales(self, info):
        query = """
            SELECT id, sale_date, customer_age, customer_gender,
                   order_quantity, profit, cost, revenue
            FROM Sales
        """
        result = execute_query(query)
        return [
            SaleType(
                id=row[0],
                saleDate=row[1].isoformat() if row[3] else None,
                customerAge=row[2],
                customerGender=row[3],
                orderQuantity=row[4],
                profit=row[5],
                cost=row[6],
                revenue=row[7]
            )
            for row in result
        ]

    def resolve_sale(self, info, id):
        query = """
            SELECT id, sale_date, customer_age, customer_gender,
                   order_quantity, profit, cost, revenue
            FROM Sales WHERE id = %s
        """
        result = execute_query(query, (id,))
        if result:
            row = result[0]
            return SaleType(
                id=row[0],
                saleDate=row[1].isoformat() if row[1] else None,
                customerAge=row[2],
                customerGender=row[3],
                orderQuantity=row[4],
                profit=row[5],
                cost=row[6],
                revenue=row[7]
            )
        return None