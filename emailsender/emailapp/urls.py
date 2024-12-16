
from django.contrib import admin
from django.urls import path , include 
from emailapp import views

urlpatterns = [
    path('index/', views.index, name='index'),  
    path('upload-excel/', views.upload_excel, name='upload_excel'),
    path('view-table/', views.view_table, name='view_table'),
    path('view-table/<str:table_name>/', views.display_table_data, name='display_table_data'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.login, name='login'),
    path('signup/', views.signup, name='signup'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('password-reset/', views.password_reset, name='password_reset'),
    path('reset-password-verify/', views.reset_password_verify, name='reset_password_verify'),
    path('reset-password-confirm/', views.reset_password_confirm, name='reset_password_confirm'),
    path('send_email/', views.send_email_page, name='send_email_page'),
    path('send_emails/', views.send_emails, name='send_email_page'),





]
