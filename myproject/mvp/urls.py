from django.urls import path, include
from . import views
from rest_framework.routers import DefaultRouter
from .views import (
    Mention_percentageViewSet,
    dashboard_data_api,
    dashboard_view,
    notification_list_api,
)
app_name = 'mvp'
router = DefaultRouter()
router.register(r'brand-percentages', Mention_percentageViewSet)
urlpatterns = [
    path('', include(router.urls)),
    path('dashboard-data/', dashboard_data_api, name='dashboard-data'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('orders/', views.order_list, name='order_list'),
    path('orders/create/', views.create_order, name='create_order'),
    path('notifications/', views.notification_list, name='notification_list'),
    path('api/notifications/', views.notification_list_api, name='notification_list_api'),
    path('unread_notification_count/', views.unread_notification_count, name='unread_notification_count'),
    path('notifications/<int:notification_id>/mark-read/', views.mark_notification_read, name='mark_notification_read'),
    path('redirect-to-create-order/', views.redirect_to_create_order, name='redirect_to_create_order'),
]
