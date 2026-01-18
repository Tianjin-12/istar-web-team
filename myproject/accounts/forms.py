from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User


class LoginForm(AuthenticationForm):
  """自定义登录表单"""
  username = forms.CharField(
    label='用户名/邮箱',
    widget=forms.TextInput(attrs={
      'class': 'form-control',
      'placeholder': '请输入用户名或邮箱',
      'autofocus': True
    })
  )
  password = forms.CharField(
    label='密码',
    widget=forms.PasswordInput(attrs={
      'class': 'form-control',
      'placeholder': '请输入密码'
    })
  )

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.error_messages['invalid_login'] = '用户名或密码错误'


class RegisterForm(UserCreationForm):
  """自定义注册表单"""
  email = forms.EmailField(
    required=True,
    label='邮箱',
    widget=forms.EmailInput(attrs={
      'class': 'form-control',
      'placeholder': '请输入邮箱地址',
      'autofocus': True
    }),
    help_text='必填，用于找回密码和接收通知'
  )
  username = forms.CharField(
    label='用户名',
    widget=forms.TextInput(attrs={
      'class': 'form-control',
      'placeholder': '请输入用户名'
    })
  )
  password1 = forms.CharField(
    label='密码',
    widget=forms.PasswordInput(attrs={
      'class': 'form-control',
      'placeholder': '请输入密码（至少8位）'
    })
  )
  password2 = forms.CharField(
    label='确认密码',
    widget=forms.PasswordInput(attrs={
      'class': 'form-control',
      'placeholder': '请再次输入密码'
    })
  )

  class Meta:
    model = User
    fields = ('username', 'email', 'password1', 'password2')

  def save(self, commit=True):
    user = super().save(commit=False)
    user.email = self.cleaned_data['email']
    if commit:
      user.save()
    return user


class EmailCodeLoginForm(forms.Form):
  """邮箱验证码登录表单（预留）"""
  email = forms.EmailField(
    label='邮箱',
    widget=forms.EmailInput(attrs={
      'class': 'form-control',
      'placeholder': '请输入邮箱地址'
    })
  )
  code = forms.CharField(
    label='验证码',
    max_length=6,
    widget=forms.TextInput(attrs={
      'class': 'form-control',
      'placeholder': '请输入6位验证码'
    })
  )


class EmailCodeResetPasswordForm(forms.Form):
  """邮箱验证码改密码表单（预留）"""
  email = forms.EmailField(
    label='邮箱',
    widget=forms.EmailInput(attrs={
      'class': 'form-control',
      'placeholder': '请输入邮箱地址'
    })
  )
  code = forms.CharField(
    label='验证码',
    max_length=6,
    widget=forms.TextInput(attrs={
      'class': 'form-control',
      'placeholder': '请输入6位验证码'
    })
  )
  new_password = forms.CharField(
    label='新密码',
    widget=forms.PasswordInput(attrs={
      'class': 'form-control',
      'placeholder': '请输入新密码（至少8位）'
    })
  )
