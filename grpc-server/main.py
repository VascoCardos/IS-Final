from concurrent import futures
from settings import GRPC_SERVER_PORT, MAX_WORKERS, MEDIA_PATH, DBNAME, DBUSERNAME, DBPASSWORD, DBHOST, DBPORT
import os
import server_services_pb2_grpc
import server_services_pb2
import grpc
import logging
import pg8000
import pandas
from lxml import etree
import time
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import pickle

# Configure logging
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("FileService")





# Servicer class for the gRPC service
class SendFileService(server_services_pb2_grpc.SendFileServiceServicer):
    def __init__(self, *args, **kwargs):
        pass

    def SendFile(self, request, context):
        os.makedirs(MEDIA_PATH, exist_ok=True)
        file_path = os.path.join(MEDIA_PATH, request.file_name + request.file_mime)
        ficheiro_em_bytes = request.file

        # Save the file
        try:
            with open(file_path, 'wb') as f:
                f.write(ficheiro_em_bytes)
            logger.info(f"File {request.file_name} saved successfully at {MEDIA_PATH}")
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}", exc_info=True)
            context.set_details(f"Failed to save file: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            return server_services_pb2.SendFileResponseBody(success=False)

        # Establish connection to PostgreSQL
        try:
            # Connect to the database
            conn = pg8000.connect(
                user=DBUSERNAME,
                password=DBPASSWORD,
                host=DBHOST,
                port=int(DBPORT),
                database=DBNAME
            )
            cursor = conn.cursor()

            # SQL query to create a table
            create_table_query = """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100),
                email VARCHAR(100) UNIQUE NOT NULL,
                age INT
            );
            """
            cursor.execute(create_table_query)
            conn.commit()
            logger.info("Database table 'users' verified/created successfully.")
            cursor.close()
            conn.close()
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}", exc_info=True)
            context.set_details(f"Database error: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            return server_services_pb2.SendFileResponseBody(success=False)

        # Response to the client
        return server_services_pb2.SendFileResponseBody(success=True)

    # Nova função SendFileChunks para lidar com o envio de chunks de arquivo
    def SendFileChunks(self, request_iterator, context):
        try:
            os.makedirs(MEDIA_PATH, exist_ok=True)
            file_name = None
            file_chunks = []  # Armazenar todos os chunks na memória

            for chunk in request_iterator:
                if not file_name:
                    file_name = chunk.file_name
                # Coletar os dados do arquivo
                file_chunks.append(chunk.data)

            # Combinar todos os chunks em um único objeto de bytes
            file_content = b"".join(file_chunks)
            file_path = os.path.join(MEDIA_PATH, file_name)

            # Escrever os dados coletados no arquivo no final
            with open(file_path, "wb") as f:
                f.write(file_content)
            logger.info(f"File {file_name} saved successfully at {MEDIA_PATH}")
            
            return server_services_pb2.SendFileChunksResponse(success=True, message="File imported successfully")

        except Exception as e:
            logger.error(f"Error: {str(e)}", exc_info=True)
            return server_services_pb2.SendFileChunksResponse(success=False, message=str(e))

    def ConvertCsvToXml(self, request, context):
        try:
            # Caminho do arquivo CSV no volume Docker
            csv_file_path = os.path.join(MEDIA_PATH, request.csv_file_name)
            xml_file_path = os.path.join(MEDIA_PATH, "Sales.xml")
            xsd_file_path = os.path.join("xsd", "Sales.xsd")

            if not os.path.exists(csv_file_path):
                error_message = f"CSV file {request.csv_file_name} not found at {MEDIA_PATH}."
                logger.error(error_message)
                context.set_details(error_message)
                context.set_code(grpc.StatusCode.NOT_FOUND)
                return server_services_pb2.ConvertCsvToXmlResponse(success=False, message=error_message)

            if not os.path.exists(xsd_file_path):
                error_message = f"XSD file Sales.xsd not found in the xsd directory."
                logger.error(error_message)
                context.set_details(error_message)
                context.set_code(grpc.StatusCode.NOT_FOUND)
                return server_services_pb2.ConvertCsvToXmlResponse(success=False, message=error_message)

            # Conversão de CSV para XML
            df = pandas.read_csv(csv_file_path)
            root = etree.Element("Sales")
            grouped = df.groupby(["Country", "State", "Latitude", "Longitude"])

            for (country, state, latitude, longitude), group in grouped:
                location = etree.SubElement(root, "Location",
                                            Country=country,
                                            State=state,
                                            Latitude=str(latitude),
                                            Longitude=str(longitude))
                products_group = group.groupby(["Product", "Product_Category", "Sub_Category", "Unit_Cost", "Unit_Price"])
                for (product, category, sub_category, unit_cost, unit_price), product_group in products_group:
                    product_elem = etree.SubElement(location, "Product",
                                                    Name=product,
                                                    Category=category,
                                                    SubCategory=sub_category,
                                                    UnitCost=str(unit_cost),
                                                    UnitPrice=str(unit_price))
                    for _, row in product_group.iterrows():
                        sale = etree.SubElement(product_elem, "Sale", Date=row["Date"])
                        etree.SubElement(sale, "CustomerAge").text = str(row["Customer_Age"])
                        etree.SubElement(sale, "CustomerGender").text = row["Customer_Gender"]
                        etree.SubElement(sale, "OrderQuantity").text = str(row["Order_Quantity"])
                        etree.SubElement(sale, "Profit").text = str(row["Profit"])
                        etree.SubElement(sale, "Cost").text = str(row["Cost"])
                        etree.SubElement(sale, "Revenue").text = str(row["Revenue"])

            # Formatando o XML
            formatted_xml = etree.tostring(root, encoding='utf-8', pretty_print=True).decode('utf-8')

            # Validar XML usando o XSD
            with open(xsd_file_path, 'r', encoding='utf-8') as xsd_file:
                xsd_doc = etree.parse(xsd_file)
                xsd_schema = etree.XMLSchema(xsd_doc)

            xml_doc = etree.fromstring(formatted_xml.encode('utf-8'))

            if not xsd_schema.validate(xml_doc):
                validation_errors = "\n".join([str(error) for error in xsd_schema.error_log])
                error_message = f"XML validation failed: {validation_errors}"
                logger.error(error_message)
                context.set_details(error_message)
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                return server_services_pb2.ConvertCsvToXmlResponse(success=False, message=error_message)


            # Salvar o XML apenas se for válido
            with open(xml_file_path, "w", encoding="utf-8") as f:
                f.write(formatted_xml)

            logger.info(f"XML file saved successfully at {xml_file_path}")
            return server_services_pb2.ConvertCsvToXmlResponse(
                success=True,
                message="CSV converted to XML successfully and XML validated successfully against XSD.",
                xml_file_name="Sales.xml"
            )

        except Exception as e:
            logger.error(f"Error: {str(e)}", exc_info=True)
            context.set_details(str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            return server_services_pb2.ConvertCsvToXmlResponse(success=False, message=str(e))

    def AddCoordinatesToCsv(self, request, context):
        try:
            # Caminho do arquivo CSV original no volume Docker
            original_csv_path = os.path.join(MEDIA_PATH, request.csv_file_name)
            updated_csv_path = os.path.join(MEDIA_PATH, "Sales_with_coordinates.csv")
            cache_file_path = os.path.join(MEDIA_PATH, "geocoding_cache.pkl")

            if not os.path.exists(original_csv_path):
                error_message = f"CSV file {request.csv_file_name} not found in {MEDIA_PATH}."
                logger.error(error_message)
                context.set_details(error_message)
                context.set_code(grpc.StatusCode.NOT_FOUND)
                return server_services_pb2.AddCoordinatesToCsvResponse(success=False, message=error_message)

            # Inicializar o geolocalizador
            geolocator = Nominatim(user_agent="geoapi")

            # Função para obter latitude e longitude com tratamento de timeout
            def get_lat_long(city, state, country):
                try:
                    location = geolocator.geocode(f"{city}, {state}, {country}")
                    if location:
                        return location.latitude, location.longitude
                    else:
                        return None, None
                except GeocoderTimedOut:
                    return None, None

            # Ler o arquivo CSV original
            df = pandas.read_csv(original_csv_path)

            # Adicionar colunas vazias para latitude e longitude se não existirem
            if 'Latitude' not in df.columns:
                df['Latitude'] = None
            if 'Longitude' not in df.columns:
                df['Longitude'] = None

            # Tentar carregar o cache salvo anteriormente (se existir)
            try:
                with open(cache_file_path, 'rb') as f:
                    geocoding_cache = pickle.load(f)
            except FileNotFoundError:
                geocoding_cache = {}

            # Lista para armazenar os índices das linhas a serem removidas
            rows_to_remove = []

            # Iterar sobre as linhas do DataFrame e adicionar as coordenadas
            for index, row in df.iterrows():
                city = row.get('City', '')
                state = row['State']
                country = row['Country']
                key = f"{city}, {state}, {country}"

                # Verificar se já temos as coordenadas no cache
                if key in geocoding_cache:
                    latitude, longitude = geocoding_cache[key]
                else:
                    # Chamar a função para obter as coordenadas
                    latitude, longitude = get_lat_long(city, state, country)
                    if latitude is not None and longitude is not None:
                        geocoding_cache[key] = (latitude, longitude)
                    else:
                        rows_to_remove.append(index)

                    # Adicionar um pequeno delay apenas quando a API é chamada
                    time.sleep(1)

                # Atribuir os valores ao DataFrame
                df.at[index, 'Latitude'] = latitude
                df.at[index, 'Longitude'] = longitude

            # Remover as linhas que não têm coordenadas
            df.drop(index=rows_to_remove, inplace=True)

            # Salvar o novo DataFrame em um novo arquivo CSV
            df.to_csv(updated_csv_path, index=False)

            # Salvar o cache em um arquivo para uso futuro
            with open(cache_file_path, 'wb') as f:
                pickle.dump(geocoding_cache, f)

            success_message = f"CSV updated with coordinates and saved to {updated_csv_path}."
            logger.info(success_message)
            return server_services_pb2.AddCoordinatesToCsvResponse(
                success=True,
                message=success_message,
                updated_csv_file_name="Sales_with_coordinates.csv"
            )

        except Exception as e:
            logger.error(f"Error: {str(e)}", exc_info=True)
            context.set_details(str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            return server_services_pb2.AddCoordinatesToCsvResponse(success=False, message=str(e))
    



    def CreateTablesAndInsertData(self, request, context):
        try:
            # Conectar ao banco de dados
            conn = pg8000.connect(
                user=DBUSERNAME,
                password=DBPASSWORD,
                host=DBHOST,
                port=int(DBPORT),
                database=DBNAME
            )
            cursor = conn.cursor()

            # SQL para criar as tabelas
            create_tables_sql = """
            CREATE TABLE IF NOT EXISTS Locations (
                id SERIAL PRIMARY KEY,
                country VARCHAR(100),
                state VARCHAR(100),
                latitude FLOAT,
                longitude FLOAT
            );

            CREATE TABLE IF NOT EXISTS Products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(150),
                category VARCHAR(100),
                sub_category VARCHAR(100),
                unit_cost NUMERIC(10, 2),
                unit_price NUMERIC(10, 2)
            );

            CREATE TABLE IF NOT EXISTS Sales (
                id SERIAL PRIMARY KEY,
                product_id INT REFERENCES Products(id),
                location_id INT REFERENCES Locations(id),
                sale_date DATE,
                customer_age INT,
                customer_gender VARCHAR(10),
                order_quantity INT,
                profit NUMERIC(10, 2),
                cost NUMERIC(10, 2),
                revenue NUMERIC(10, 2)
            );
            """
            cursor.execute(create_tables_sql)
            conn.commit()

            # Caminho do XML no volume Docker
            xml_file_path = os.path.join(MEDIA_PATH, "Sales.xml")

            if not os.path.exists(xml_file_path):
                error_message = f"XML file not found at {xml_file_path}."
                context.set_details(error_message)
                context.set_code(grpc.StatusCode.NOT_FOUND)
                return server_services_pb2.CreateTablesAndInsertDataResponse(success=False, message=error_message)

            # Ler e parsear o XML
            tree = etree.parse(xml_file_path)
            root = tree.getroot()

            # Inserir os dados no banco de dados
            for location in root.findall("Location"):
                country = location.attrib["Country"]
                state = location.attrib["State"]
                latitude = location.attrib["Latitude"]
                longitude = location.attrib["Longitude"]

                # Inserir localização
                cursor.execute(
                    "INSERT INTO Locations (country, state, latitude, longitude) VALUES (%s, %s, %s, %s) RETURNING id;",
                    (country, state, latitude, longitude)
                )
                location_id = cursor.fetchone()[0]

                for product in location.findall("Product"):
                    name = product.attrib["Name"]
                    category = product.attrib["Category"]
                    sub_category = product.attrib["SubCategory"]
                    unit_cost = product.attrib["UnitCost"]
                    unit_price = product.attrib["UnitPrice"]

                    # Inserir produto
                    cursor.execute(
                        "INSERT INTO Products (name, category, sub_category, unit_cost, unit_price) VALUES (%s, %s, %s, %s, %s) RETURNING id;",
                        (name, category, sub_category, unit_cost, unit_price)
                    )
                    product_id = cursor.fetchone()[0]

                    for sale in product.findall("Sale"):
                        sale_date = sale.attrib["Date"]
                        customer_age = sale.find("CustomerAge").text
                        customer_gender = sale.find("CustomerGender").text
                        order_quantity = sale.find("OrderQuantity").text
                        profit = sale.find("Profit").text
                        cost = sale.find("Cost").text
                        revenue = sale.find("Revenue").text

                        # Inserir venda
                        cursor.execute(
                            """
                            INSERT INTO Sales (product_id, location_id, sale_date, customer_age, customer_gender, order_quantity, profit, cost, revenue)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                            """,
                            (product_id, location_id, sale_date, customer_age, customer_gender, order_quantity, profit, cost, revenue)
                        )
            conn.commit()
            cursor.close()
            conn.close()

            success_message = "Tables created and data inserted successfully."
            return server_services_pb2.CreateTablesAndInsertDataResponse(success=True, message=success_message)

        except Exception as e:
            context.set_details(str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            return server_services_pb2.CreateTablesAndInsertDataResponse(success=False, message=str(e))
    def GetSalesByCountry(self, request, context):
        """
        Retorna as vendas totais por país com base no XML.
        """
        import xml.etree.ElementTree as ET

        file_path = "/app/media/Sales.xml"

        try:
            # Carregar o XML
            tree = ET.parse(file_path)
            root = tree.getroot()

            # Consulta XPath para vendas por país
            sales_data = {}
            for location in root.findall(".//Location"):
                country = location.get("Country")
                sales = sum(
                    float(sale.find("Profit").text)
                    for sale in location.findall(".//Sale")
                )
                sales_data[country] = sales_data.get(country, 0) + sales

            # Construir a resposta
            response = server_services_pb2.GetSalesByCountryResponse()
            for country, total_sales in sales_data.items():
                response.sales_by_country.add(country=country, total_sales=total_sales)

            return response

        except Exception as e:
            logger.error(f"Error processing XML: {str(e)}", exc_info=True)
            context.set_details(str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            return server_services_pb2.GetSalesByCountryResponse()

    def ListProfitableProducts(self, request, context):
        try:
            # Caminho do arquivo XML no volume Docker
            xml_file_path = "/app/media/Sales.xml"

            # Verificar se o arquivo existe
            if not os.path.exists(xml_file_path):
                return server_services_pb2.ListProfitableProductsResponse(
                    success=False,
                    message=f"XML file not found at {xml_file_path}"
                )

            # Carregar o arquivo XML
            with open(xml_file_path, "rb") as f:
                tree = etree.parse(f)

            # Montar o XPath
            xpath_query = f"""
                //Product[Sale[Profit > {request.profit_threshold} and @Date="{request.date}"]]
            """

            # Executar o XPath
            products = tree.xpath(xpath_query)

            # Criar a resposta
            product_list = []
            for product in products:
                product_list.append(server_services_pb2.ProductDetails(
                    name=product.attrib['Name'],
                    category=product.attrib['Category'],
                    sub_category=product.attrib['SubCategory']
                ))

            return server_services_pb2.ListProfitableProductsResponse(
                success=True,
                products=product_list
            )

        except Exception as e:
            return server_services_pb2.ListProfitableProductsResponse(
                success=False,
                message=str(e)
            )

    def CalculateDiscountedSales(self, request, context):
        try:
            # Caminho do arquivo XML
            xml_file_path = "/app/media/Sales.xml"
            
            # Carregar e analisar o XML
            with open(xml_file_path, "rb") as xml_file:
                xml_tree = etree.parse(xml_file)

            # XPath para encontrar todas as vendas
            sales = xml_tree.xpath("//Location")
            result = []

            for location in sales:
                city = location.get("State")  # Obtém a cidade (state)
                
                # Encontrar as vendas com maior desconto nesta cidade
                max_discount = None
                best_sale_info = None

                for product in location.xpath(".//Product"):
                    unit_price = float(product.get("UnitPrice"))

                    for sale in product.xpath(".//Sale"):
                        order_quantity = int(sale.xpath("OrderQuantity/text()")[0])
                        revenue = float(sale.xpath("Revenue/text()")[0])
                        
                        # Calcula o desconto
                        total_cost = order_quantity * unit_price
                        if total_cost > revenue:
                            discount = total_cost - revenue
                            if max_discount is None or discount > max_discount:
                                max_discount = discount
                                best_sale_info = {
                                    "City": city,
                                    "Discount": discount,
                                    "OrderQuantity": order_quantity,
                                    "Revenue": revenue,
                                    "UnitPrice": unit_price,
                                    "CustomerAge": int(sale.xpath("CustomerAge/text()")[0]),
                                    "CustomerGender": sale.xpath("CustomerGender/text()")[0],
                                    "Date": sale.get("Date"),
                                }

                if best_sale_info:
                    result.append(best_sale_info)

            return server_services_pb2.CalculateDiscountedSalesResponse(
                success=True,
                sales=[
                    server_services_pb2.SaleInfo(
                        City=sale["City"],
                        Discount=sale["Discount"],
                        OrderQuantity=sale["OrderQuantity"],
                        Revenue=sale["Revenue"],
                        UnitPrice=sale["UnitPrice"],
                        CustomerAge=sale["CustomerAge"],
                        CustomerGender=sale["CustomerGender"],
                        Date=sale["Date"]
                    )
                    for sale in result
                ]
            )
        except Exception as e:
            logger.error(f"Error in CalculateDiscountedSales: {str(e)}", exc_info=True)
            return server_services_pb2.CalculateDiscountedSalesResponse(
                success=False,
                error_message=str(e)
            )

    def GetSalesByGender(self, request, context):
        try:
            # Caminho para o arquivo XML
            xml_file_path = "/app/media/Sales.xml"

            # Carregar o XML
            tree = etree.parse(xml_file_path)

            # XPath para selecionar vendas dentro do intervalo de idade
            xpath_expression = (
                f"//Sale[CustomerAge >= {request.min_age} and CustomerAge <= {request.max_age}]"
            )
            sales = tree.xpath(xpath_expression)

            # Contadores para total de compras por gênero
            total_sales_m = 0
            total_sales_f = 0

            for sale in sales:
                gender = sale.find("CustomerGender").text
                order_quantity = int(sale.find("OrderQuantity").text)

                if gender == "M":
                    total_sales_m += order_quantity
                elif gender == "F":
                    total_sales_f += order_quantity

            return server_services_pb2.GetSalesByGenderResponse(
                success=True,
                total_sales_m=total_sales_m,
                total_sales_f=total_sales_f,
            )
        except Exception as e:
            return server_services_pb2.GetSalesByGenderResponse(
                success=False, message=str(e)
            )        




# Função para iniciar o servidor gRPC
def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=MAX_WORKERS))
    server_services_pb2_grpc.add_SendFileServiceServicer_to_server(SendFileService(), server)
    server.add_insecure_port(f'[::]:{GRPC_SERVER_PORT}')
    logger.info(f"Starting gRPC server on port {GRPC_SERVER_PORT}")
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
