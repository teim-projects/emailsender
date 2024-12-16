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











import re
from django.core.exceptions import ValidationError
from django.core.mail import send_mail, BadHeaderError
from django.contrib import messages
from django.shortcuts import render, redirect
from twilio.rest import Client
from emailapp.models import OTP, CustomUser




def validate_phone_number(phone):
    pattern = re.compile(r'^\+\d{10,15}$')  # E.164 format
    if not pattern.match(phone):
        raise ValidationError("Invalid phone number format. Use E.164 format (e.g., +1234567890).")
    return phone

def send_otp_email(email, otp_code):
    try:
        send_mail(
            'Account Verification',
            f'Your OTP for signup is: {otp_code}',
            'noreply@myapp.com',
            [email]
        )
    except BadHeaderError:
        raise ValidationError("Invalid email header found.")
    except Exception as e:
        raise ValidationError(f"Error sending email: {e}")
    

from twilio.rest import Client
import os

def send_otp_sms(mobile, otp_code):
    try:
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        client = Client(account_sid, auth_token)

        message = client.messages.create(
            body=f"Your OTP for signup is: {otp_code}",
            from_=os.getenv("TWILIO_PHONE_NUMBER"),
            to=mobile
        )
    except Exception as e:
        raise ValidationError(f"Error sending SMS: {e}")



def signup(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        country_code = request.POST.get('country_code')  # Get the selected country code
        mobile = request.POST.get('mobile')  # Get the mobile number
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        # Combine the country code and mobile number
        full_mobile_number = f"{country_code}{mobile}"

        # Validate the phone number format (e.g., E.164)
        try:
            full_mobile_number = validate_phone_number(full_mobile_number)
        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('signup')

        # Check for existing email or mobile
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, f"User with email ({email}) already exists.")
            return redirect('signup')

        if CustomUser.objects.filter(mobile=full_mobile_number).exists():
            messages.error(request, f"User with mobile number ({full_mobile_number}) already exists.")
            return redirect('signup')

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('signup')

        # Create user and send OTP
        user = CustomUser.objects.create_user(email=email, mobile=full_mobile_number, password=password)
        user.is_active = False
        user.save()

        otp_code = OTP.generate_otp()
        OTP.objects.create(user=user, code=otp_code)

        # Send OTP via Email
        try:
            send_otp_email(email, otp_code)
        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('signup')
               
               
        # # Send OTP via Voice Call


        # try:
        #     send_otp_call(full_mobile_number, otp_code)
        #     messages.success(request, "An OTP call has been made to your mobile. Please listen to the OTP.")
        # except Exception as e:
        #     messages.error(request, f"Error sending OTP call: {e}")
        #     return redirect('signup')

        # Send OTP via SMS using Twilio
        try:
            send_otp_sms(full_mobile_number, otp_code)
        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('signup')

        messages.success(request, "Signup successful. Please verify your email and mobile.")
        request.session['user_id'] = user.id
        return redirect('verify_otp')

    return render(request, 'signup.html')



from django.core.mail import send_mail, BadHeaderError
from django.utils.timezone import now, timedelta

def verify_otp(request):
    if request.method == 'POST':
        user_id = request.session.get('user_id')
        user = CustomUser.objects.get(id=user_id)
        entered_otp = request.POST['otp']

        # Retrieve OTP and check for time validity
        otp = OTP.objects.filter(user=user, code=entered_otp).first()
        
        # Get the count of OTP attempts from session
        otp_attempts = request.session.get('otp_attempts', 0)

        if otp and otp.created_at >= now() - timedelta(minutes=10):
            # Successful OTP validation
            user.is_active = True
            user.is_verified = True
            user.save()
            OTP.objects.filter(user=user).delete()  # Delete OTP after use
            
            # Send a welcome email
            try:
                send_mail(
                    'Welcome to Our Institute!',
                    f'Hi {user.email},\n\nWelcome to our institute! We are excited to have you with us.',
                    'welcome@myapp.com',
                    [user.email],
                )
            except BadHeaderError:
                messages.error(request, "Invalid header found while sending welcome email.")
            except Exception as e:
                messages.error(request, f"Error sending welcome email: {e}")

            # Clear session data for OTP attempts
            request.session.pop('otp_attempts', None)
            
            messages.success(request, "Signup successful and welcome email sent.")
            return redirect('/')
        else:
            # Increment OTP attempts
            otp_attempts += 1
            request.session['otp_attempts'] = otp_attempts
            messages.error(request, "Invalid OTP. Please try again.")
            
            # Check if attempts exceeded the limit
            if otp_attempts >= 2:
                OTP.objects.filter(user=user).delete()
                request.session.pop('otp_attempts', None)  # Reset attempts
                return redirect('signup')
    return render(request, 'verify_otp.html')



from django.contrib.auth import login as auth_login  # Ensure proper login function import
from django.shortcuts import redirect, render
from django.contrib import messages
from .models import CustomUser

def login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Clear user session data
        request.session.pop('user_email', None)

        # Regular user login logic
        try:
            user = CustomUser.objects.get(email=email)
            if user.check_password(password):  # Validate the password
                auth_login(request, user)  # Log the user in
                request.session['user_email'] = user.email
                return redirect('index')  # Redirect to the user's dashboard
            else:
                # Incorrect password
                messages.error(request, "Incorrect password. Please try again.")
        except CustomUser.DoesNotExist:
            # Email not found in the system
            messages.error(request, "User with this email does not exist. Please register.")

    # Render login page with potential error messages
    return render(request, 'login.html')


from django.shortcuts import redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required

def logout_view(request):
    logout(request)  # Logs out the user
    return redirect('login')


def password_reset(request):
    if request.method == 'POST':
        email = request.POST['email']
        user = CustomUser.objects.filter(email=email).first()
        if user:
            otp_code = OTP.generate_otp()
            OTP.objects.create(user=user, code=otp_code)
            send_mail(
                'Password Reset Request',
                f'Your password reset OTP is: {otp_code}',
                'noreply@myapp.com',
                [email]
            )
            request.session['reset_user_id'] = user.id
            return redirect('reset_password_verify')
        messages.error(request, "Email not found")
    return render(request, 'password_reset.html')



from django.utils import timezone

def reset_password_verify(request):
    if request.method == 'POST':
        reset_user_id = request.session.get('reset_user_id')
        user = CustomUser.objects.get(id=reset_user_id)
        entered_otp = request.POST['otp']

        otp = OTP.objects.filter(user=user, code=entered_otp).first()

        if otp and otp.created_at >= timezone.now() - timedelta(minutes=10):
            return redirect('reset_password_confirm')
        messages.error(request, "Invalid OTP")
    return render(request, 'reset_password_verify.html')


def reset_password_confirm(request):
    if request.method == 'POST':
        reset_user_id = request.session.get('reset_user_id')
        user = CustomUser.objects.get(id=reset_user_id)
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        if password == confirm_password:
            user.set_password(password)
            user.save()
            messages.success(request, "Password reset successful")
            return redirect('login')
        messages.error(request, "Passwords do not match")
    return render(request, 'reset_password_confirm.html')




from django.shortcuts import render, redirect
from django.db import connection
from django.core.mail import send_mail
from django.conf import settings
from .models import UploadedTable

def send_email_page(request):
    if request.method == 'POST':
        sender_email = request.POST.get('sender_email')
        table_name = request.POST.get('table_name')

        if not sender_email or not table_name:
            return render(request, 'send_email.html', {
                'error': 'Please provide both sender email and table name.',
                'tables': UploadedTable.objects.values_list('table_name', flat=True),
            })

        try:
            # Fetch email addresses from the selected table
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT email FROM {table_name}")
                emails = [row[0] for row in cursor.fetchall()]

            # Send email to all fetched email addresses
            subject = "Welcome to TEIM"
            message = "Thank you for joining TEIM! We are excited to have you with us."

            for email in emails:
                send_mail(subject, message, sender_email, [email], fail_silently=False)

            return render(request, 'send_email.html', {
                'success': f"Emails sent successfully to {len(emails)} customers.",
                'tables': UploadedTable.objects.values_list('table_name', flat=True),
            })

        except Exception as e:
            return render(request, 'send_email.html', {
                'error': f"Error sending emails: {e}",
                'tables': UploadedTable.objects.values_list('table_name', flat=True),
            })

    # Render the email sending page with table list
    tables = UploadedTable.objects.values_list('table_name', flat=True)
    return render(request, 'send_email.html', {'tables': tables})

from django.shortcuts import render
from django.db import connection  # For dynamic table queries
from django.http import JsonResponse
import asyncio

async def send_emails(request):
    success = None
    error = None
    sent_count = 0
    total_count = 0

    # Fetch the table names dynamically (example)
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
        )
        tables = [row[0] for row in cursor.fetchall()]

    if request.method == "POST":
        sender_email = request.POST.get("sender_email")
        table_name = request.POST.get("table_name")

        if not sender_email or not table_name:
            error = "Both fields are required."
        else:
            try:
                # Fetch customer emails from the selected table
                with connection.cursor() as cursor:
                    cursor.execute(f"SELECT email FROM {table_name}")
                    customers = [row[0] for row in cursor.fetchall()]

                total_count = len(customers)

                # Simulate email sending asynchronously
                for customer_email in customers:
                    await asyncio.sleep(1)  # Simulate async email sending
                    sent_count += 1

                success = f"Successfully sent emails to {sent_count}/{total_count} customers."

            except Exception as e:
                error = f"Error occurred: {str(e)}"

    return render(request, "send_emails.html", {
        "tables": tables,
        "success": success,
        "error": error,
    })
