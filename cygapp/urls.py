from django.conf.urls import patterns, include, url
from django.contrib import admin
import settings
import group_views, device_views, product_views, policy_views, login_views
import enforcement_views, package_views, file_views, views

admin.autodiscover()

urlpatterns = patterns('',
        url(r'^media/(?P<path>.*)$','django.views.static.serve',
            {'document_root': settings.MEDIA_ROOT}),

        #Management CRUD views
        url(r'^$', views.overview, name='overview'),
        url(r'^overview/?$', views.overview, name='overview'),

        url(r'^login/?$', login_views.login, name='login'),
        
        url(r'^groups/?$', group_views.groups, name='groups'),
        url(r'^groups/(?P<groupID>\d+)/?$', group_views.group, name='group'),
        url(r'^groups/add/?$', group_views.add, name='add'),
        url(r'^groups/save?$', group_views.save, name='save'),
        url(r'^groups/(?P<groupID>\d+)/delete/?$', group_views.delete,
            name='delete'),

        url(r'^devices/?$', device_views.devices, name='devices'),
        url(r'^devices/(?P<deviceID>\d+)/?$', device_views.device, name='device'),
        url(r'^devices/add/?$', device_views.add, name='add'),
        url(r'^devices/save?$', device_views.save, name='save'),
        url(r'^devices/(?P<deviceID>\d+)/delete/?$', device_views.delete,
            name='delete'),

        url(r'^devices/(?P<deviceID>\d+)/simulate/?$', device_views.simulate,
            name='simulate'),

        url(r'^files/?$', file_views.files, name='files'),
        url(r'^files/(?P<fileID>\d+)/?$', file_views.file, name='file'),
        url(r'^files/save?$', file_views.save, name='save'),
        url(r'^files/(?P<fileID>\d+)/delete/?$', file_views.delete,
            name='delete'),

        url(r'^file_hashes/(?P<file_hashID>\d+)/delete/?$', file_views.deleteHash,
            name='delete'),
    
        url(r'^packages/?$', package_views.packages, name='packages'),
        url(r'^packages/(?P<packageID>\d+)/?$', package_views.package, name='package'),
        url(r'^packages/add/?$', package_views.add, name='add'),
        url(r'^packages/save?$', package_views.save, name='save'),
        url(r'^packages/(?P<packageID>\d+)/delete/?$', package_views.delete,
            name='delete'),
        url(r'^packages/search/?$', package_views.search, name='search'),

        url(r'^versions/(?P<versionID>\d+)/toggle/?$',
            package_views.toggle_version, name='toggle_version'),
        
        url(r'^products/?$', product_views.products, name='products'),
        url(r'^products/(?P<productID>\d+)/?$', product_views.product, name='product'),
        url(r'^products/add/?$', product_views.add, name='product_add'),
        url(r'^products/save?$', product_views.save, name='product_save'),
        url(r'^products/(?P<productID>\d+)/delete/?$', product_views.delete,
            name='delete'),
        
        url(r'^policies/?$', policy_views.policies, name='policies'),
        url(r'^policies/(?P<policyID>\d+)/?$', policy_views.policy, name='policy'),
        url(r'^policies/add/?$', policy_views.add, name='add'),
        url(r'^policies/save?$', policy_views.save, name='save'),
        url(r'^policies/(?P<policyID>\d+)/delete/?$', policy_views.delete,
            name='delete'),
        
        url(r'^enforcements/?$', enforcement_views.enforcements,
            name='enforcements'),
        url(r'^enforcements/(?P<enforcementID>\d+)/?$', enforcement_views.enforcement, name='enforcement'),
        url(r'^enforcements/add/?$', enforcement_views.add, name='add'),
        url(r'^enforcements/save?$', enforcement_views.save, name='save'),
        url(r'^enforcements/(?P<enforcementID>\d+)/delete/?$', enforcement_views.delete,
            name='delete'),
        
        #IMV API patterns
        url(r'^cmd/start_session/?$', views.start_session,
            name='start_session'),

        url(r'^cmd/end_session/?$', views.end_session,
            name='end_session'),

        #==============================================

        #To enable built-in admin-interface:
        url(r'^admin/', include(admin.site.urls)),
        )
