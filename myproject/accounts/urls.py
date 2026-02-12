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
    
    path('send-verification-code/', views.send_verification_code, name='send_verification_code'),
    path('register-with-code/', views.register_with_code, name='register_with_code'),
    path('reset-password-with-code/', views.reset_password_with_code, name='reset_password_with_code'),
    path('deregister-and-reregister/', views.deregister_and_reregister, name='deregister_and_reregister'),
    
    path('reset-password/email-code/', views.emailCodeResetPasswordView, name='emailCodeResetPassword'),
]
