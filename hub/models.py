from django.db import models
from django.contrib.auth.models import User

class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    phone = models.CharField(max_length=15)
    address = models.TextField()

    def __str__(self):
        return self.user.get_full_name() or self.user.username



# ==========================================
# SERVICE
# ==========================================

class Service(models.Model):

    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


# ==========================================
# WORKER
# ==========================================

class Worker(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    phone = models.CharField(max_length=15)
    place = models.CharField(max_length=100)
    experience = models.IntegerField()
    description = models.TextField(blank=True)

    services = models.ManyToManyField(Service)

    availability = models.BooleanField(default=True)

    approval_status = models.CharField(
        max_length=20,
        default="PENDING"
    )

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Booking(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)

    booking_date = models.DateField()
    booking_time = models.TimeField()

    address = models.TextField()
    description = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        default="PENDING"
    )

    created_at = models.DateTimeField(auto_now_add=True)


class Rating(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField()
    review = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"{self.worker} - {self.rating}"