from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.decorators.cache import never_cache
from .models import Worker, Service,Customer,Booking,Rating
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Avg, Count
import re

@never_cache
def splash(request):
    return render(request, "splash.html")

@never_cache
def home(request):
    return render(request, 'home.html')

@never_cache
def register(request):

    if request.method == "POST":

        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        address = request.POST.get("address", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        errors = {}

        # --------------------------------
        # NAME VALIDATION
        # --------------------------------

        if not name:
            errors["name"] = "Name is required."

        elif not re.fullmatch(r"[A-Za-z ]+", name):
            errors["name"] = "Name should contain only letters."


        # --------------------------------
        # EMAIL VALIDATION
        # --------------------------------

        if not email:
            errors["email"] = "Email address is required."

        elif not re.fullmatch(
            r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$",
            email
        ):
            errors["email"] = "Enter a valid email address."

        elif User.objects.filter(username=email).exists():
            errors["email"] = "An account with this email already exists."


        # --------------------------------
        # PHONE VALIDATION
        # --------------------------------

        if not phone:
            errors["phone"] = "Phone number is required."

        elif not phone.isdigit():
            errors["phone"] = "Phone number should contain only digits."

        elif len(phone) != 10:
            errors["phone"] = "Phone number must contain exactly 10 digits."


        # --------------------------------
        # ADDRESS VALIDATION
        # --------------------------------

        if not address:
            errors["address"] = "Address is required."

        elif len(address) < 5:
            errors["address"] = "Please enter a valid address."


        # --------------------------------
        # PASSWORD VALIDATION
        # --------------------------------

        if not password:
            errors["password"] = "Password is required."

        elif len(password) < 8:
            errors["password"] = "Password must contain at least 8 characters."


        # --------------------------------
        # CONFIRM PASSWORD
        # --------------------------------

        if not confirm_password:
            errors["confirm_password"] = "Please confirm your password."

        elif password != confirm_password:
            errors["confirm_password"] = "Passwords do not match."


        # --------------------------------
        # IF ERRORS EXIST
        # --------------------------------

        if errors:

            return render(
                request,
                "customer_register.html",
                {
                    "errors": errors,
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "address": address,
                }
            )


        # --------------------------------
        # CREATE USER
        # --------------------------------

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=name
        )


        # --------------------------------
        # CREATE CUSTOMER
        # --------------------------------

        Customer.objects.create(
            user=user,
            phone=phone,
            address=address
        )


        messages.success(
            request,
            "Registration successful! Please login."
        )

        return redirect("login")


    return render(request, "customer_register.html")

@never_cache
def login(request):

    if request.method == "POST":

        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")


        if not username:

            messages.error(
                request,
                "Email address is required."
            )

            return render(
                request,
                "customer_login.html"
            )


        if not password:

            messages.error(
                request,
                "Password is required."
            )

            return render(
                request,
                "customer_login.html"
            )


        user = authenticate(
            request,
            username=username,
            password=password
        )


        if user is not None:

            if Customer.objects.filter(user=user).exists():

                auth_login(request, user)
                request.session["customer_id"] = user.id

                return redirect("customer")

            else:

                messages.error(
                    request,
                    "This account is not registered as a customer."
                )

        else:

            messages.error(
                request,
                "Invalid email or password."
            )


    return render(
        request,
        "customer_login.html"
    )




@never_cache
def customer(request):


    customer_id = request.session.get("customer_id")

    if not customer_id:
        return redirect("login")

    try:
        customer = Customer.objects.get(user=request.user)
    except Customer.DoesNotExist:
        messages.error(request, "Customer profile not found.")
        return redirect("login")

    bookings = Booking.objects.filter(
        customer=customer
    ).select_related(
        "worker__user",
        "service"
    ).prefetch_related(
        "rating"
    ).order_by("-created_at")

    return render(
        request,
        "customer.html",
        {
            "user": request.user,
            "customer": customer,
            "bookings": bookings
        }
    )


@never_cache
def logout(request):

    request.session.flush()

    return redirect("login")

@never_cache
def rate_worker(request, booking_id):

    if not request.user.is_authenticated:
        return redirect("login")

    try:
        customer = Customer.objects.get(user=request.user)
    except Customer.DoesNotExist:
        messages.error(request, "Customer profile not found.")
        return redirect("login")


    try:
        booking = Booking.objects.select_related(
            "worker__user",
            "service"
        ).get(
            id=booking_id,
            customer=customer
        )

    except Booking.DoesNotExist:
        messages.error(request, "Booking not found.")
        return redirect("customer")


    # Only completed jobs can be rated

    if booking.status != "COMPLETED":
        messages.error(
            request,
            "You can rate a worker only after the job is completed."
        )
        return redirect("customer")


    # Prevent rating the same booking twice

    if Rating.objects.filter(booking=booking).exists():
        messages.info(
            request,
            "You have already rated this booking."
        )
        return redirect("customer")


    if request.method == "POST":

        rating_value = request.POST.get("rating")
        review = request.POST.get("review", "")


        Rating.objects.create(
            booking=booking,
            customer=customer,
            worker=booking.worker,
            rating=rating_value,
            review=review
        )


        messages.success(
            request,
            "Thank you! Your rating has been submitted."
        )

        return redirect("customer")


    return render(request, "rate_worker.html", {
        "booking": booking
    })


def worker_register(request):

    if request.method == "POST":

        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        place = request.POST.get("place", "").strip()
        service_name = request.POST.get("service", "").strip()
        experience = request.POST.get("experience", "").strip()
        description = request.POST.get("description", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        errors = {}

        # NAME
        if not name:
            errors["name"] = "Full name is required."

        elif not re.fullmatch(r"[A-Za-z ]+", name):
            errors["name"] = "Name should contain only letters and spaces."


        # EMAIL
        if not email:
            errors["email"] = "Email address is required."

        elif not re.fullmatch(
            r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$",
            email
        ):
            errors["email"] = "Enter a valid email address."

        elif User.objects.filter(username=email).exists():
            errors["email"] = "An account with this email already exists."


        # PHONE
        if not phone:
            errors["phone"] = "Phone number is required."

        elif not phone.isdigit():
            errors["phone"] = "Phone number should contain only digits."

        elif len(phone) != 10:
            errors["phone"] = "Phone number must contain exactly 10 digits."


        # PLACE
        if not place:
            errors["place"] = "Place is required."


        # SERVICE
        if not service_name:
            errors["service"] = "Please select a service."


        # EXPERIENCE
        if not experience:
            errors["experience"] = "Years of experience is required."

        else:
            try:
                experience_value = int(experience)

                if experience_value < 0:
                    errors["experience"] = "Experience cannot be negative."

            except ValueError:
                errors["experience"] = "Enter a valid number."


        # DESCRIPTION
        if not description:
            errors["description"] = "Please describe your service."

        elif len(description) < 10:
            errors["description"] = (
                "Please enter at least 10 characters."
            )


        # PASSWORD
        if not password:
            errors["password"] = "Password is required."

        elif len(password) < 8:
            errors["password"] = (
                "Password must contain at least 8 characters."
            )


        # CONFIRM PASSWORD
        if not confirm_password:
            errors["confirm_password"] = (
                "Please confirm your password."
            )

        elif password != confirm_password:
            errors["confirm_password"] = (
                "Passwords do not match."
            )


        # IF THERE ARE ERRORS
        if errors:

            return render(
                request,
                "worker_register.html",
                {
                    "errors": errors,
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "place": place,
                    "service": service_name,
                    "experience": experience,
                    "description": description,
                }
            )


        # CREATE USER
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=name
        )


        # CREATE WORKER
        worker = Worker.objects.create(
            user=user,
            phone=phone,
            place=place,
            experience=experience_value,
            description=description,
            approval_status="PENDING"
        )


        # CREATE / GET SERVICE
        service, created = Service.objects.get_or_create(
            name=service_name,
            defaults={"category": "HOME"}
        )

        worker.services.add(service)


        messages.success(
            request,
            "Registration submitted successfully. "
            "Please wait for admin approval."
        )

        return redirect("worker_login")


    return render(request, "worker_register.html")


@never_cache
def worker_login(request):

    if request.method == "POST":

        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")


        if not email:

            messages.error(
                request,
                "Email address is required."
            )

            return render(request, "worker_login.html")


        if not password:

            messages.error(
                request,
                "Password is required."
            )

            return render(request, "worker_login.html")


        try:

            worker = Worker.objects.get(
                user__email=email
            )

        except Worker.DoesNotExist:

            messages.error(
                request,
                "No worker account found with this email."
            )

            return render(request, "worker_login.html")


        # CHECK ADMIN APPROVAL

        if worker.approval_status != "APPROVED":

            if worker.approval_status == "PENDING":

                messages.error(
                    request,
                    "Your registration is waiting for admin approval."
                )

            elif worker.approval_status == "REJECTED":

                messages.error(
                    request,
                    "Your registration was rejected by the administrator."
                )

            return render(request, "worker_login.html")


        # CHECK PASSWORD

        user = authenticate(
            request,
            username=worker.user.username,
            password=password
        )


        if user is not None:

            auth_login(request, user)

            return redirect("worker")


        messages.error(
            request,
            "Invalid email or password."
        )


    return render(request, "worker_login.html")


@never_cache
def worker(request):
    if not request.user.is_authenticated:
        return redirect("worker_login")

    try:
        worker = Worker.objects.get(user=request.user)
    except Worker.DoesNotExist:
        messages.error(request, "Worker account not found.")
        return redirect("worker_login")

    if worker.approval_status != "APPROVED":
        auth_logout(request)
        messages.error(request, "Your worker account is not approved.")
        return redirect("worker_login")

    # Get ALL bookings for this worker
    jobs = Booking.objects.filter(
        worker=worker
    ).order_by("-booking_date", "booking_time")

    pending_count = Booking.objects.filter(
        worker=worker,
        status="PENDING"
    ).count()

    completed_count = Booking.objects.filter(
        worker=worker,
        status="COMPLETED"
    ).count()

    ratings = Rating.objects.filter(worker=worker)

    if ratings.exists():
        average_rating = round(
            sum(r.rating for r in ratings) / ratings.count(),
            1
        )
    else:
        average_rating = 0.0

    return render(request, "worker.html", {
        "worker": worker,
        "jobs": jobs,
        "pending_count": pending_count,
        "completed_count": completed_count,
        "average_rating": average_rating,
    })

@never_cache
def workers(request):
    if not request.user.is_authenticated:
        return redirect("login")

    service_name = request.GET.get("service")

    selected_service = None
    worker_list = Worker.objects.filter(
        approval_status="APPROVED",
        availability=True
    ).annotate(
        average_rating=Avg("rating__rating"),
        rating_count=Count("rating")
    )

    if service_name:
        selected_service = Service.objects.filter(
            name__iexact=service_name
        ).first()

        if selected_service:
            worker_list = worker_list.filter(
                services=selected_service
            )
        else:
            worker_list = Worker.objects.none()

    return render(request, "workers.html", {
        "workers": worker_list,
        "selected_service": selected_service,
    })

@never_cache
def complete_booking(request, booking_id):

    if not request.user.is_authenticated:
        return redirect("worker_login")

    try:
        worker = Worker.objects.get(user=request.user)
    except Worker.DoesNotExist:
        messages.error(request, "Worker account not found.")
        return redirect("worker_login")

    if worker.approval_status != "APPROVED":
        messages.error(request, "Your worker account is not approved.")
        return redirect("worker_login")

    if request.method == "POST":

        try:
            booking = Booking.objects.get(
                id=booking_id,
                worker=worker
            )

            booking.status = "COMPLETED"
            booking.save()

            messages.success(
                request,
                "Job marked as completed successfully."
            )

        except Booking.DoesNotExist:

            messages.error(
                request,
                "Booking not found."
            )

    return redirect("worker")

@never_cache
def edit_worker_profile(request):

    if not request.user.is_authenticated:
        return redirect("worker_login")

    try:
        worker = Worker.objects.get(user=request.user)
    except Worker.DoesNotExist:
        messages.error(request, "Worker account not found.")
        return redirect("worker_login")

    if worker.approval_status != "APPROVED":
        messages.error(request, "Your worker account is not approved.")
        return redirect("worker_login")

    if request.method == "POST":

        name = request.POST.get("name")
        phone = request.POST.get("phone")
        place = request.POST.get("place")
        experience = request.POST.get("experience")
        description = request.POST.get("description")

        # Update User details
        worker.user.first_name = name
        worker.user.save()

        # Update Worker details
        worker.phone = phone
        worker.place = place
        worker.experience = experience
        worker.description = description
        worker.save()

        messages.success(
            request,
            "Profile updated successfully."
        )

        return redirect("worker")

    return render(request, "edit_worker_profile.html", {
        "worker": worker
    })


@never_cache
def booking(request):

    if not request.user.is_authenticated:
        return redirect("login")

    try:
        customer = Customer.objects.get(user=request.user)
    except Customer.DoesNotExist:
        messages.error(request, "Customer profile not found.")
        return redirect("login")

    # When customer submits the booking form
    if request.method == "POST":

        worker_id = request.POST.get("worker")
        service_id = request.POST.get("service")
        booking_date = request.POST.get("booking_date")
        booking_time = request.POST.get("booking_time")
        address = request.POST.get("address")
        description = request.POST.get("description")

        try:
            worker = Worker.objects.get(
                id=worker_id,
                approval_status="APPROVED",
                availability=True
            )

            service = Service.objects.get(id=service_id)

        except (Worker.DoesNotExist, Service.DoesNotExist):
            messages.error(request, "Invalid worker or service selected.")
            return redirect("customer")

        Booking.objects.create(
            customer=customer,
            worker=worker,
            service=service,
            booking_date=booking_date,
            booking_time=booking_time,
            address=address,
            description=description,
            status="PENDING"
        )

        messages.success(
            request,
            "Service booked successfully!"
        )

        return redirect("customer")

    # Show available workers and services
    workers = Worker.objects.filter(
        approval_status="APPROVED",
        availability=True
    )

    services = Service.objects.all()

    return render(
        request,
        "booking.html",
        {
            "workers": workers,
            "services": services
        }
    )

def admin_required(view_func):
    return user_passes_test(
        lambda user: user.is_authenticated and user.is_superuser,
        login_url="admin_login"
    )(view_func)


def admin_login(request):

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None and user.is_superuser:

            auth_login(request, user)

            return redirect("admin_dashboard")

        messages.error(
            request,
            "Invalid admin username or password."
        )

    return render(request, "admin_login.html")


@admin_required
def admin_dashboard(request):

    return render(
        request,
        "admin_dashboard.html"
    )

@never_cache
def admin_logout(request):
    auth_logout(request)
    return redirect("admin_login")

@admin_required
def service_management(request):

    services = Service.objects.all().order_by("id")

    return render(
        request,
        "service_management.html",
        {
            "services": services
        }
    )



@admin_required
def add_service(request):

    if request.method == "POST":

        name = request.POST.get("name")
        category = request.POST.get("category")
        description = request.POST.get("description")

        Service.objects.create(
            name=name,
            category=category,
            description=description
        )

        messages.success(request, "Service added successfully.")

        return redirect("service_management")

    return render(request, "add_service.html")


@admin_required
def edit_service(request, service_id):

    service = get_object_or_404(Service, id=service_id)

    if request.method == "POST":

        name = request.POST.get("name")
        category = request.POST.get("category")
        description = request.POST.get("description")

        service.name = name
        service.category = category
        service.description = description

        service.save()

        messages.success(request, "Service updated successfully.")

        return redirect("service_management")

    return render(request, "edit_service.html", {
        "service": service
    })

@admin_required
def delete_service(request, service_id):

    service = get_object_or_404(Service, id=service_id)

    if request.method == "POST":

        service.delete()

        messages.success(request, "Service deleted successfully.")

    return redirect("service_management")

@admin_required
def worker_management(request):

    pending_workers = Worker.objects.filter(
        approval_status="PENDING"
    ).order_by("-id")

    approved_workers = Worker.objects.filter(
        approval_status="APPROVED"
    ).order_by("-id")

    return render(
        request,
        "worker_management.html",
        {
            "pending_workers": pending_workers,
            "approved_workers": approved_workers,
        }
    )


@admin_required
def approve_worker(request, worker_id):

    if request.method == "POST":

        try:
            worker = Worker.objects.get(
                id=worker_id,
                approval_status="PENDING"
            )

            worker.approval_status = "APPROVED"
            worker.save()

            messages.success(
                request,
                "Worker approved successfully."
            )

        except Worker.DoesNotExist:

            messages.error(
                request,
                "Worker request not found."
            )

    return redirect("worker_management")

@admin_required
def reject_worker(request, worker_id):

    if request.method == "POST":

        try:
            worker = Worker.objects.get(
                id=worker_id,
                approval_status="PENDING"
            )

            worker.approval_status = "REJECTED"
            worker.save()

            messages.success(
                request,
                "Worker request rejected."
            )

        except Worker.DoesNotExist:

            messages.error(
                request,
                "Worker request not found."
            )

    return redirect("worker_management")

@never_cache
@admin_required
def customer_management(request):
    customers = Customer.objects.select_related("user").all().order_by("-id")

    return render(request, "customer_management.html", {
        "customers": customers
    })

@never_cache
@admin_required
def booking_management(request):
    bookings = Booking.objects.select_related(
        "customer__user",
        "worker__user",
        "service"
    ).all().order_by("-created_at")

    return render(request, "booking_management.html", {
        "bookings": bookings
    })