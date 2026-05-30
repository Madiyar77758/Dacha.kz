from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("property/<int:pk>/", views.property_detail, name="property_detail"),
    path("favorites/", views.favorites_list, name="favorites"),
    path("favorites/toggle/<int:pk>/", views.favorite_toggle, name="favorite_toggle"),
    # Кабинет хоста
    path("host/", views.host_dashboard, name="host_dashboard"),
    path("host/bookings/", views.host_bookings, name="host_bookings"),
    path("host/new/", views.property_create, name="property_create"),
    path("host/<int:pk>/edit/", views.property_edit, name="property_edit"),
    path("host/<int:pk>/calendar/", views.property_calendar, name="property_calendar"),
    path("host/analytics/", views.host_analytics, name="host_analytics"),
    path("api/properties.json", views.properties_geojson, name="properties_geojson"),
]
