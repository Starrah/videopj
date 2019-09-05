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
    path('admin/', admin.site.urls),
    re_path(r'^image/(?P<path>.*)', serve, {"document_root": MEDIA_ROOT}),
    re_path("^test$", views.test),
    re_path("^test2$", views.test2),
    re_path("^login$", views.login),
    re_path("^logon$", views.logon),
    re_path("^logout$", views.logout),
    re_path("^loginPage$", views.loginPage),
    re_path("^uploadPage$", views.uploadPage),
    re_path("^upload$", views.upload),
    re_path("^resultPage$", views.resultPage),
    re_path("^queryResult$", views.queryResult),
    re_path("^history$", views.history),
    re_path("^delete$", views.delete),
    re_path("^adminHistory$", views.adminHistory),
    re_path("^adminUser$", views.adminUser),
    re_path("^adminDeleteUser$", views.adminDeleteUser),
]

REDIRECT_DICT = {
    "^login$": "loginPage",
    "^logon$": "loginPage",
    "^delete$": "history",
    "^upload$": "uploadPage",
}
