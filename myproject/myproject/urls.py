"""
URL configuration for myproject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Import an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function:  from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from mvp.views import (
  dashboard_view,
  geo_evaluate_view,
  ai_toxic_view,
  cgeo_wiki_view,
  about_view,
)
from mvp import views

urlpatterns = [
  path('admin/', admin.site.urls),
  path('api/', include('mvp.urls')),
  path('accounts/', include('accounts.urls')),
  path('', dashboard_view, name='dashboard'),
  path('dashboard/brand/', dashboard_view, name='dashboard_brand'),
  path('dashboard/geo-evaluate/', geo_evaluate_view, name='dashboard_geo_evaluate'),
  path('dashboard/ai-toxic/', ai_toxic_view, name='dashboard_ai_toxic'),
  path('dashboard/cgeo-wiki/', cgeo_wiki_view, name='dashboard_cgeo_wiki'),
  path('dashboard/about/', about_view, name='dashboard_about'),
  path('orders/', views.order_list, name='order_list'),
  path('orders/create/', views.create_order, name='create_order'),
  path('notifications/', views.notification_list, name='notification_list'),
  path('dash/', include('django_plotly_dash.urls')),
]
