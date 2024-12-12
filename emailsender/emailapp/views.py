from django.shortcuts import render , redirect

# Create your views here.

def index(request):
    return render(request,'index.html')
import os
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.shortcuts import render, redirect
import pandas as pd
from django.db import connection
from .models import UploadedTable

def upload_excel(request):
    if request.method == 'POST':
        table_name = request.POST.get('table_name')
        excel_file = request.FILES.get('excel_file')

        if not table_name or not excel_file:
            return render(request, 'upload_excel.html', {'error': 'Please provide both table name and Excel file.'})

        # Save the uploaded file temporarily
        fs = FileSystemStorage()
        file_path = fs.save(excel_file.name, excel_file)
        file_full_path = os.path.join(settings.MEDIA_ROOT, file_path)

        try:
            # Read the Excel file into a DataFrame
            data = pd.read_excel(file_full_path)

            # Replace NaN values with None
            data = data.where(pd.notnull(data), None)

            # Check if the table already exists in the database (optional)
            # You can choose to skip this if you trust that tables are unique per user.
            if UploadedTable.objects.filter(table_name=table_name).exists():
                return render(request, 'upload_excel.html', {'error': 'Table with this name already exists. Please choose a different name.'})

            # Save the uploaded table name to the UploadedTable model
            UploadedTable.objects.get_or_create(table_name=table_name)

            # Create a SQL table dynamically based on the DataFrame structure
            with connection.cursor() as cursor:
                # Generate SQL to create the table
                create_table_query = f"CREATE TABLE `{table_name}` ("
                for column in data.columns:
                    create_table_query += f"`{column}` VARCHAR(255), "
                create_table_query = create_table_query.rstrip(', ') + ')'
                cursor.execute(create_table_query)

                # Insert data into the newly created table
                for _, row in data.iterrows():
                    placeholders = ', '.join(['%s'] * len(row))
                    insert_query = f"INSERT INTO `{table_name}` VALUES ({placeholders})"
                    cursor.execute(insert_query, tuple(row))

            # Store success message in the session
            request.session['success'] = f"Table '{table_name}' created successfully with data."
            return redirect('upload_excel')

        except Exception as e:
            return render(request, 'upload_excel.html', {'error': f"Error processing Excel file: {e}"})
        finally:
            # Clean up the uploaded file
            if os.path.exists(file_full_path):
                os.remove(file_full_path)

    # Get success message from the session if available
    success_message = request.session.pop('success', None)
    return render(request, 'upload_excel.html', {'success': success_message})


from django.shortcuts import render, redirect
import pandas as pd
from django.db import connection
from django.shortcuts import render, redirect
from .models import UploadedTable

def view_table(request):
    tables = UploadedTable.objects.values_list('table_name', flat=True)
    print(tables)  # Add this line to check if data is being fetched correctly
    return render(request, 'view_table.html', {'tables': tables})



def display_table_data(request, table_name):
    # Fetch data and columns for the selected table
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT * FROM {table_name}")
        data = cursor.fetchall()
        columns = [col[0] for col in cursor.description]

    return render(request, 'display_table_data.html', {
        'table_name': table_name,
        'columns': columns,
        'data': data,
    })
