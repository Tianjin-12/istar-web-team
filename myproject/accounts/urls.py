from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
  path('login/', views.loginView, name='login'),
  path('register/', views.registerView, name='register'),
  path('logout/', views.logoutView, name='logout'),
  path('profile/', views.profileView, name='profile'),

  path('api/auth-check/', views.apiAuthCheck, name='apiAuthCheck'),
  path('api/logout/', views.apiLogout, name='apiLogout'),

  path('reset-password/email-code/', views.emailCodeResetPasswordView, name='emailCodeResetPassword'),
]
