from django.urls import path

from . import views

urlpatterns = [
    path("create/<int:property_id>/", views.create, name="booking_create"),
    path("<int:pk>/pay/", views.pay, name="booking_pay"),
    path("<int:pk>/cancel/", views.cancel, name="booking_cancel"),
    path("<int:pk>/decision/", views.host_decision, name="booking_decision"),
    path("<int:pk>/review/", views.review_create, name="review_create"),
    path("mine/", views.my_bookings, name="my_bookings"),
]
