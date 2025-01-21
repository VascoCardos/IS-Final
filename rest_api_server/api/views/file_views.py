from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..serializers.file_serializer import FileUploadSerializer
import os
import grpc
import api.grpc.server_services_pb2 as server_services_pb2
import api.grpc.server_services_pb2_grpc as server_services_pb2_grpc
from rest_api_server.settings import GRPC_HOST, GRPC_PORT

class FileUploadView(APIView):
    def post(self, request):
        serializer = FileUploadSerializer(data=request.data)

        if serializer.is_valid():
            file = serializer.validated_data['file']

            if not file:
                return Response(
                    {"error": "No file uploaded"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Extrair o nome e a extensão do arquivo usando os.path.splitext
            file_name, file_extension = os.path.splitext(file.name)

            # Ler o conteúdo do arquivo
            file_content = file.read()

            # Conectar ao serviço gRPC
            channel = grpc.insecure_channel(f'{GRPC_HOST}:{GRPC_PORT}')
            stub = server_services_pb2_grpc.SendFileServiceStub(channel)

            # Preparar o pedido gRPC
            grpc_request = server_services_pb2.SendFileRequestBody(
                file_name=file_name,
                file_mime=file_extension,
                file=file_content
            )

            # Enviar os dados do arquivo para o serviço gRPC
            try:
                response = stub.SendFile(grpc_request)
                return Response(
                    {
                        "file_name": file_name,
                        "file_extension": file_extension,
                        "message": response.message  # Supondo que a resposta tenha um campo 'message'
                    },
                    status=status.HTTP_201_CREATED
                )
            except grpc.RpcError as e:
                return Response(
                    {"error": f"gRPC call failed: {e.details()}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

class FileUploadChunksView(APIView):
    def post(self, request):
        serializer = FileUploadSerializer(data=request.data)

        if serializer.is_valid():
            file = serializer.validated_data['file']

            if not file:
                return Response(
                    {"error": "No file uploaded"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Conectar ao serviço gRPC
            channel = grpc.insecure_channel(f'{GRPC_HOST}:{GRPC_PORT}')
            stub = server_services_pb2_grpc.SendFileServiceStub(channel)

            def generate_file_chunks(file, file_name, chunk_size=(64 * 1024)):
                """
                Gera os chunks do arquivo para envio.
                """
                try:
                    while chunk := file.read(chunk_size):
                        yield server_services_pb2.SendFileChunksRequest(
                            data=chunk,
                            file_name=file_name
                        )
                except Exception as e:
                    print(f"Error reading file: {e}")
                    raise  # Propagar a exceção

            # Enviar os chunks do arquivo para o serviço gRPC
            try:
                response = stub.SendFileChunks(generate_file_chunks(file, file.name, (64 * 1024)))
                if response.success:
                    return Response(
                        {"file_name": file.name},
                        status=status.HTTP_201_CREATED
                    )
                return Response(
                    {"error": f"gRPC response error: {response.message}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            except grpc.RpcError as e:
                return Response(
                    {"error": f"gRPC call failed: {e.details()}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
class ConvertCsvToXmlView(APIView):
    """
    View para converter um arquivo CSV em XML.
    """
    def post(self, request):
        # Verificar se o nome do arquivo CSV foi fornecido
        csv_file_name = request.data.get('csv_file_name')
        
        if not csv_file_name:
            return Response(
                {"error": "csv_file_name is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Conectar ao serviço gRPC
        channel = grpc.insecure_channel(f'{GRPC_HOST}:{GRPC_PORT}')
        stub = server_services_pb2_grpc.SendFileServiceStub(channel)

        # Preparar o pedido gRPC
        grpc_request = server_services_pb2.ConvertCsvToXmlRequest(
            csv_file_name=csv_file_name
        )

        # Chamar o método gRPC para converter o CSV em XML
        try:
            response = stub.ConvertCsvToXml(grpc_request)

            # Verificar a resposta do gRPC
            if response.success:
                return Response(
                    {
                        "message": response.message,
                        "xml_file_name": response.xml_file_name  # Caminho do arquivo XML gerado
                    },
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"error": response.message},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except grpc.RpcError as e:
            return Response(
                {"error": f"gRPC call failed: {e.details()}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class AddCoordinatesToCsvView(APIView):
    def post(self, request):
        csv_file_name = request.data.get('csv_file_name')

        if not csv_file_name:
            return Response({"error": "csv_file_name is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Conectar ao serviço gRPC
        channel = grpc.insecure_channel(f'{GRPC_HOST}:{GRPC_PORT}')
        stub = server_services_pb2_grpc.SendFileServiceStub(channel)

        grpc_request = server_services_pb2.AddCoordinatesToCsvRequest(csv_file_name=csv_file_name)

        try:
            response = stub.AddCoordinatesToCsv(grpc_request)
            if response.success:
                return Response(
                    {
                        "success": response.success,
                        "message": response.message,
                        "updated_csv_file_name": response.updated_csv_file_name
                    },
                    status=status.HTTP_200_OK
                )
            return Response({"error": response.message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except grpc.RpcError as e:
            return Response({"error": f"gRPC call failed: {e.details()}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class GetSalesByCountryView(APIView):
    def get(self, request):
        # Conectar ao gRPC
        channel = grpc.insecure_channel(f'{GRPC_HOST}:{GRPC_PORT}')
        stub = server_services_pb2_grpc.SendFileServiceStub(channel)

        grpc_request = server_services_pb2.GetSalesByCountryRequest()

        try:
            # Enviar a requisição ao gRPC
            response = stub.GetSalesByCountry(grpc_request)

            # Converter a resposta para um formato adequado para JSON
            sales_data = [
                {"country": item.country, "total_sales": item.total_sales}
                for item in response.sales_by_country
            ]
            return Response({"sales_by_country": sales_data}, status=status.HTTP_200_OK)
        except grpc.RpcError as e:
            return Response(
                {"error": f"gRPC call failed: {e.details()}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        
        
class CreateTablesAndInsertDataView(APIView):
    def post(self, request):
        # Conectar ao gRPC
        channel = grpc.insecure_channel(f'{GRPC_HOST}:{GRPC_PORT}')
        stub = server_services_pb2_grpc.SendFileServiceStub(channel)

        grpc_request = server_services_pb2.CreateTablesAndInsertDataRequest()

        try:
            # Enviar a requisição ao gRPC
            response = stub.CreateTablesAndInsertData(grpc_request)
            if response.success:
                return Response({"message": response.message}, status=status.HTTP_201_CREATED)
            return Response({"error": response.message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except grpc.RpcError as e:
            return Response(
                {"error": f"gRPC call failed: {e.details()}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        

class ListProfitableProductsView(APIView):
    """
    View para listar produtos lucrativos.
    """
    def post(self, request):
        profit_threshold = request.data.get('profit_threshold')
        date = request.data.get('date')

        if not profit_threshold or not date:
            return Response(
                {"error": "profit_threshold and date are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Conectar ao serviço gRPC
        channel = grpc.insecure_channel(f'{GRPC_HOST}:{GRPC_PORT}')
        stub = server_services_pb2_grpc.SendFileServiceStub(channel)

        grpc_request = server_services_pb2.ListProfitableProductsRequest(
            profit_threshold=float(profit_threshold),
            date=date
        )

        try:
            # Chamar o método gRPC
            response = stub.ListProfitableProducts(grpc_request)

            if response.success:
                return Response(
                    {
                        "products": [
                            {
                                "name": product.name,
                                "category": product.category,
                                "sub_category": product.sub_category
                            } for product in response.products
                        ]
                    },
                    status=status.HTTP_200_OK
                )
            else:
                return Response({"error": response.message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except grpc.RpcError as e:
            return Response(
                {"error": f"gRPC call failed: {e.details()}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CalculateDiscountedSalesView(APIView):
    def get(self, request):
        # Extrair parâmetros de consulta da URL
        discount_rate = float(request.query_params.get("discount_rate", 0.1))  # Default: 10%
        start_date = request.query_params.get("start_date", "2023-01-01")  # Data padrão
        end_date = request.query_params.get("end_date", "2023-12-31")  # Data padrão

        # Conectar ao gRPC
        channel = grpc.insecure_channel(f'{GRPC_HOST}:{GRPC_PORT}')
        stub = server_services_pb2_grpc.SendFileServiceStub(channel)

        try:
            # Criar a requisição gRPC
            grpc_request = server_services_pb2.CalculateDiscountedSalesRequest(
                discount_rate=discount_rate,
                start_date=start_date,
                end_date=end_date
            )

            # Fazer a chamada ao gRPC
            response = stub.CalculateDiscountedSales(grpc_request)

            if response.success:
                return Response(
                    {"sales": [
                        {
                            "City": sale.City,
                            "Discount": sale.Discount,
                            "OrderQuantity": sale.OrderQuantity,
                            "Revenue": sale.Revenue,
                            "UnitPrice": sale.UnitPrice,
                            "CustomerAge": sale.CustomerAge,
                            "CustomerGender": sale.CustomerGender,
                            "Date": sale.Date,
                        }
                        for sale in response.sales
                    ]},
                    status=status.HTTP_200_OK
                )
            else:
                return Response({"error": response.error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except grpc.RpcError as e:
            return Response({"error": f"gRPC call failed: {e.details()}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class GetSalesByGenderView(APIView):
    def post(self, request):
        min_age = request.data.get("min_age")
        max_age = request.data.get("max_age")

        # Validação básica
        if min_age is None or max_age is None:
            return Response(
                {"error": "Both 'min_age' and 'max_age' are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            min_age = int(min_age)
            max_age = int(max_age)
        except ValueError:
            return Response(
                {"error": "'min_age' and 'max_age' must be integers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Conectar ao serviço gRPC
        channel = grpc.insecure_channel(f"{GRPC_HOST}:{GRPC_PORT}")
        stub = server_services_pb2_grpc.SendFileServiceStub(channel)

        grpc_request = server_services_pb2.GetSalesByGenderRequest(
            min_age=min_age, max_age=max_age
        )

        try:
            response = stub.GetSalesByGender(grpc_request)

            if response.success:
                return Response(
                    {
                        "total_sales_m": response.total_sales_m,
                        "total_sales_f": response.total_sales_f,
                    },
                    status=status.HTTP_200_OK,
                )
            return Response(
                {"error": response.message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except grpc.RpcError as e:
            return Response(
                {"error": f"gRPC call failed: {e.details()}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
