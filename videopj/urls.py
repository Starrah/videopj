"""videopj URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, re_path
from django.views.static import serve
from imagebkd import views
from .settings import MEDIA_ROOT


urlpatterns = [
    path('sysAdmin/', admin.site.urls),
    re_path(r"^$", views.indexRedi),
    re_path(r'^image/(?P<path>.*)', serve, {"document_root": MEDIA_ROOT}),
    re_path(r"^login$", views.login),
    re_path(r"^logon$", views.logon),
    re_path(r"^logout$", views.logout),
    re_path(r"^loginPage$", views.loginPage),
    re_path(r"^uploadPage$", views.uploadPage),
    re_path(r"^upload$", views.upload),
    re_path(r"^resultPage$", views.resultPage),
    re_path(r"^queryResult$", views.queryResult),
    re_path(r"^history$", views.history),
    re_path(r"^delete$", views.delete),
    re_path(r"^admin$", views.adminRedi),
    re_path(r"^adminHistory$", views.adminHistory),
    re_path(r"^adminUser$", views.adminUser),
    re_path(r"^adminDeleteUser$", views.adminDeleteUser),
]

REDIRECT_DICT = {
    r"^login$": "loginPage",
    r"^logon$": "loginPage",
    r"^delete$": "history",
    r"^upload$": "uploadPage",
    r"^resultPage$": "uploadPage",
    r"^adminDeleteUser$": "adminUsers"
}
