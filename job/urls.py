from django.contrib import admin
from django.urls import path, include
from . import views
from django.http import HttpResponse

def ads_txt(request):
    return HttpResponse(
        "google.com, pub-XXXXXXXXXXXXXXXX, DIRECT, f08c47fec0942fa0",
        content_type="text/plain"
    )
urlpatterns = [
    path('',views.main, name='main'),
    path('register/',views.register, name='register'),
    path('login/',views.user_login, name='login'),
    path('job_seeker_dashboard/',views.job_seeker_dashboard, name='job_seeker_dashboard'),
    path('recommended_jobs/',views.recommended_jobs, name='recommended_jobs'),
    path('user_activity/',views.login_activity_view, name='user_activity'),
    path('employer_dashboard/',views.employer_dashboard, name='employer_dashboard'),
    path('userlist/',views.userlist, name='userlist'),
    path('company_profile/',views.company_profile, name='company_profile'),
    path('my_resume/',views.my_resume, name='my_resume'),
    path('browse_jobs/',views.browse_jobs, name='browse_jobs'),
    path('post_jobs/',views.post_jobs, name='post_jobs'),
    path('compaines/',views.compaines, name='compaines'),
    path('manage_jobs/',views.manage_jobs, name='manage_jobs'),
    path('companies_homepage/',views.companies_homepage, name='companies_homepage'),
    path('myapplications/',views.myapplications, name='myapplications'),
    path('view_applicants/<int:id>',views.view_applicants, name='view_applicants'),
    path('view_jobdetail/<int:id>',views.view_jobdetail, name='view_jobdetail'),
    path('edit_job/<int:id>',views.edit_job, name='edit_job'),
    path('edit_seeker_profile/<int:id>',views.edit_seeker_profile, name='edit_seeker_profile'),
    path('delete_job/<int:id>',views.delete_job, name='delete_job'),
    path('delete_job_admin/<int:id>',views.delete_job_admin, name='delete_job_admin'),
    path('apply_job/<int:id>',views.apply_job, name='apply_job'),
    path('myjob/',views.myjob, name='myjob'),
    path('user_setting/',views.user_setting, name='user_setting'),

    path('update_application_status/<int:id>',views.update_application_status, name='update_application_status'),
    path('aboutus/',views.aboutus, name='aboutus'),
    path('seeker_profile/',views.seeker_profile, name='seeker_profile'),
    path('admin_home/',views.admin_home, name='admin_home'),
    path('delete_job_applications/<int:id>',views.delete_job_applications, name='delete_job_applications'),
    path('admin_dashboard/',views.admin_dashboard, name='admin_dashboard'),
    path('view_application/<int:id>',views.view_application, name='view_application'),
    path('all_jobs_admin/',views.all_jobs, name='all_jobs_admin'),
    path('view_all_applicants_employer/',views.view_all_applicants_employer, name='view_all_applicants_employer'),
    path('saved_jobs/',views.saved_jobs, name='saved_jobs'),
    path('job_applied_show_admin/',views.job_applied_show_admin, name='job_applied_show_admin'),
    path('toggle-save-job/<int:job_id>/', views.toggle_save_job, name='toggle_save_job'),
    path('company_job_list/<int:id>/', views.company_job_list, name='company_job_list'),
    path('delete_user/<int:id>/', views.delete_user, name='delete_user'),
    path('accounts/login/',views.user_login, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/read/<int:pk>/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark_all_read/', views.mark_all_notifications_read_ajax, name='mark_all_notifications_read_ajax'),
    path('applications/withdraw/<int:app_id>/', views.withdraw_application, name='withdraw_application'),
    path("ads.txt", ads_txt, name="ads_txt"),
    path('toggle_user_status/<int:user_id>/', views.toggle_user_status, name='toggle_user_status'),







]