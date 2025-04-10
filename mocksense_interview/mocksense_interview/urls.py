from django.contrib import admin
from django.urls import path,include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('apti/',include('aptitude.urls')),
    path('mock_interview/', include('mock_interview.urls')),
    path('group_discussion/', include('group_discussion.urls')),
    path('gd/', include('group_discussion.urls')),
    path('', include('accounts.urls')),
    path('techmcq/', include('techmcq.urls')),
]
