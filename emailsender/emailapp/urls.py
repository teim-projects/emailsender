
from django.contrib import admin
from django.urls import path , include 
from emailapp import views

urlpatterns = [
    path('', views.index),
    path('upload-excel/', views.upload_excel, name='upload_excel'),
    path('view-table/', views.view_table, name='view_table'),
    path('view-table/<str:table_name>/', views.display_table_data, name='display_table_data'),




]
