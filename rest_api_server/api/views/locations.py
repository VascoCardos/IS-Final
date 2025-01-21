from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import connection

class GetAllLocations(APIView):
    def get(self, request):
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, country, state, latitude, longitude FROM Locations")
            result = cursor.fetchall()

        locations = [
            {
                "id": row[0],
                "country": row[1],
                "state": row[2],
                "latitude": row[3],
                "longitude": row[4],
            }
            for row in result
        ]

        return Response({"locations": locations}, status=status.HTTP_200_OK)
