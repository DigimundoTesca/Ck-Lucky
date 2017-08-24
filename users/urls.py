ble File  33 lines (24 sloc)  973 Bytes
from django.conf import settings
from django.conf.urls import url

from users import views

app_name = 'users'

urlpatterns = [

]

if settings.DEBUG:
    # urlpatterns.append(url(r'^register/test', views.test, name='register_test'))
    pass
