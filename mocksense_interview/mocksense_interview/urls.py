"""
URL configuration for mocksense_interview project.

    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function view
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')

    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('apti/',include('aptitude.urls')),
    path('mock_interview/', include('mock_interview.urls')),
    path('group_discussion/', include('group_discussion.urls')),
    path('gd/', include('group_discussion.urls')),
    path('', include('accounts.urls')),
    path('mcq/', include('techmcq.urls')),
]
