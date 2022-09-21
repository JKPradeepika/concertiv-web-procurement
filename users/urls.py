from django.urls import path
from .views import *

app_name = 'users'

urlpatterns = [
    path('login/', AdminLogin.as_view(), name='login'),
    path('login/home', AdminLogin.as_view(), name='login'),
    path('logout/', AdminLogout.as_view(), name='logout'),
    path('profile/', AdminProfile.as_view(), name='profile'),
]
