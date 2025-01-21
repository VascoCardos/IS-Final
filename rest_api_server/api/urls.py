from django.urls import path
from api.views.file_views import FileUploadView, FileUploadChunksView,  ConvertCsvToXmlView, AddCoordinatesToCsvView, CreateTablesAndInsertDataView, GetSalesByCountryView, ListProfitableProductsView, CalculateDiscountedSalesView, GetSalesByGenderView
from .views.users import GetAllUsers
from .views.locations import GetAllLocations

urlpatterns = [
    path('upload-file/', FileUploadView.as_view(), name='uploadfile'),
    path('upload-file/by-chunks', FileUploadChunksView.as_view(), name='upload-file-by-chunks'),
    path('convert-csv-to-xml/', ConvertCsvToXmlView.as_view(), name='convert-csv-to-xml'),
    path('add-coordinates-to-csv/', AddCoordinatesToCsvView.as_view(), name='add_coordinates_to_csv'),
    path('users/', GetAllUsers.as_view(), name='users'),
    path("create-tables-and-insert-data/", CreateTablesAndInsertDataView.as_view(), name="create_tables_and_insert_data"),
    path('get-sales-by-country/', GetSalesByCountryView.as_view(), name='get_sales_by_country'),
    path('list-profitable-products/', ListProfitableProductsView.as_view(), name='list-profitable-products'),
    path("calculate-discounted-sales/", CalculateDiscountedSalesView.as_view(), name="calculate_discounted_sales"),
    path('sales-by-gender/', GetSalesByGenderView.as_view(), name='sales_by_gender'),
    path('get_locations/', GetAllLocations.as_view(), name='locations'),
]
