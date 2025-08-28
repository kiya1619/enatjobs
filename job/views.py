from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from .models import EmployerProfile, JobSeekerProfile
from django.contrib.auth import authenticate, login, logout     
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Job, JobCategory, Application, EmployerProfile, SeekerProfile, SavedJob, Skill, JobCategory, Notification2
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from .models import Job, JobApplication
from django.utils import timezone
from django.db import models
import json
from functools import wraps
from django.http import HttpResponseRedirect
from .decorators import role_required
import json
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.conf import settings
from .models import Notification
from django.utils.timezone import now
from django.db.models import Q  
from django.db.models.functions import ExtractMonth
from django.db.models import Count
import datetime
from django.db.models import Count, Q, F, ExpressionWrapper, FloatField
from job.skills import skills 
from django.db.models import Value, Func, F
from django.db.models.functions import Replace, Lower
from django.http import JsonResponse

User = get_user_model()

def register(request):
    if request.method == 'POST':
        username = request.POST['username'].lower()
        email = request.POST['email']
        password1 = request.POST['password1']
        password2 = request.POST['password2']
        role = request.POST['role']
        
        if password1 != password2:
            return render(request, 'register.html', {'error': 'Passwords do not match'})
        
        user = User.objects.create(
            username=username,
            email=email,
            password=make_password(password1),
            is_employer=(role=='employer'),
            is_job_seeker=(role=='jobseeker')
        )
        
        if role == 'employer':
            EmployerProfile.objects.create(user=user, comapany_name=username)
       
        return redirect('login')
    
    return render(request, 'job/register.html')

def main(request):
    return render(request, 'job/main.html')


def userlist(request):
    users = User.objects.all()
    return render(request, 'job/userlist.html', {'users': users})
from django.contrib import messages
from django.contrib.auth import authenticate, login, get_user_model
from django.shortcuts import render, redirect

User = get_user_model()


def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').lower()
        password = request.POST.get('password')

        # Authenticate user (doesn't reveal if username exists)
        user = authenticate(request, username=username, password=password)

        if user is None:
            # Generic error message
            messages.error(request, "Invalid username or password")
            return redirect('login')

        # Login & redirect based on role
        login(request, user)
        if getattr(user, 'is_employer', False):
            return redirect('employer_dashboard')
        elif getattr(user, 'is_job_seeker', False):
            return redirect('job_seeker_dashboard')
        elif user.is_superuser:
            return redirect('admin_dashboard')

    return render(request, 'job/login.html')


@role_required('employer')
def employer_dashboard(request):
    employer = EmployerProfile.objects.get(user=request.user)

    # Jobs by employer
    jobs = Job.objects.filter(employer=employer).order_by('-posted_on')
    active_jobs = jobs.filter(is_active=True).count()
    expired_jobs = jobs.filter(is_active=False).count()

    # Applications grouped by status
    applications = JobApplication.objects.filter(job__employer=employer)
    applications_count = applications.count()
    apps_status_count = applications.values('status').annotate(total=Count('id'))

    # Make status dictionary
    apps_status_dict = {entry['status']: entry['total'] for entry in apps_status_count}

    # Recent applicants
    recent_applications = applications.select_related('applicant', 'job').order_by('-applied_on')[:5]

    context = {
        "employer": employer,
        "active_jobs": active_jobs,
        "expired_jobs": expired_jobs,
        "jobs_count": jobs.count(),
        "applications_count": applications_count,
        "apps_status": apps_status_dict,
        "recent_applications": recent_applications,
    }
    return render(request, 'job/employer_dashboard.html',context)
@role_required('job_seeker')
def job_seeker_dashboard(request):
    user = request.user
    try:
        seeker_profile = SeekerProfile.objects.get(user=user)
    except SeekerProfile.DoesNotExist:
        messages.warning(request, "Please complete your profile to get job recommendations.")
        return redirect('seeker_profile')

    # 1. Get job IDs the user already applied for
    applied_jobs = JobApplication.objects.filter(applicant=user).values_list('job_id', flat=True)

    # 2. Fetch only active jobs, exclude applied ones
    jobs = Job.objects.filter(
        is_active=True,
        deadline__gte=timezone.now().date()
    ).exclude(id__in=applied_jobs)

    # 3. Annotate skill matches
    jobs = jobs.annotate(
        skill_match_count=Count(
            'required_skills',
            filter=Q(required_skills__in=seeker_profile.skills.all())
        )
    )

    # 4. Calculate location match & total score
    for job in jobs:
        job.location_match = 1 if seeker_profile.location and job.location.lower() in seeker_profile.location.lower() else 0
        job.total_score = job.skill_match_count * 2 + job.location_match

    # 5. Sort jobs by total_score descending
    recommended_jobs = sorted(jobs, key=lambda j: j.total_score, reverse=True)

    context = {
        'user': user,
        'recommended_jobs': recommended_jobs,
    }
    return render(request, 'job/job_seeker_dashboard.html', context)
def logout_user(request):
    logout(request)
    return redirect('login')

from django.core.paginator import Paginator
from django.utils import timezone
from django.db import models
from django.db.models import Value, CharField
from django.db.models.functions import Replace, Lower
from django.shortcuts import render

def browse_jobs(request):
    applied_jobs = []
    saved_jobs = []

    if request.user.is_authenticated:
        saved_jobs = request.user.savedjob_set.values_list('job_id', flat=True)
        applied_jobs = JobApplication.objects.filter(applicant=request.user).values_list('job_id', flat=True)

    # Get search parameters
    search_query = request.GET.get('search', '')
    location_query = request.GET.get('location', '')
    category_query = request.GET.get('category', '')


    # Start with active jobs
    jobs = Job.objects.filter(deadline__gte=timezone.now(), is_active=True)

    # Apply search filters
    if search_query:
        normalized_query = search_query.replace(" ", "").lower()
        jobs = jobs.annotate(
            clean_title=Replace(Lower("title"), Value(" "), Value(""), output_field=CharField()),
            clean_description=Replace(Lower("description"), Value(" "), Value(""), output_field=CharField()),
            clean_employer=Replace(Lower("employer__comapany_name"), Value(" "), Value(""), output_field=CharField()),
            clean_location=Replace(Lower("location"), Value(" "), Value(""), output_field=CharField()),
            clean_category=Replace(Lower("category__name"), Value(" "), Value(""), output_field=CharField()),
        ).filter(
            models.Q(clean_title__icontains=normalized_query) |
            models.Q(clean_description__icontains=normalized_query) |
            models.Q(clean_employer__icontains=normalized_query) |
            models.Q(clean_location__icontains=normalized_query) |
            models.Q(clean_category__icontains=normalized_query)
        )

    if location_query:
        jobs = jobs.filter(location__icontains=location_query)
    if category_query:
        jobs = jobs.filter(category_id=category_query)
    # Order by most recent
    jobs = jobs.order_by('-posted_on')

    # Pagination (9 jobs per page)
    paginator = Paginator(jobs, 9)
    page_number = request.GET.get('page')
    jobs_page = paginator.get_page(page_number)

    context = {
        'jobs': jobs_page,
        'search_query': search_query,
        'location_query': location_query,
        'total_jobs': jobs.count(),
        'applied_jobs': applied_jobs,
        'saved_jobs': saved_jobs,
        'categories': JobCategory.objects.all(), 
    }

    return render(request, 'job/browse_jobs.html', context)
@login_required
def view_jobdetail(request, id):
    job = get_object_or_404(Job, id=id)
    already_applied = JobApplication.objects.filter(job=job, applicant=request.user).exists()
    similar_jobs = Job.objects.filter(category=job.category).exclude(id=job.id)[:4]

    context = {
        'job': job,
        'already_applied': already_applied,
        'similar_jobs': similar_jobs
    }
    return render(request, 'job/view_jobdetail.html', context)
@role_required('employer')
def edit_job(request, id):
    ethiopian_cities = [
        "Addis Ababa", "Mekelle", "Gondar", "Adama", "Bahir Dar", "Dire Dawa",
        "Hawassa", "Jimma", "Shashamane", "Bishoftu", "Sodo", "Arba Minch",
        "Jijiga", "Hosaena", "Kombolcha", "Dila", "Nekemte", "Debre Birhan",
        "Debre Markos", "Asella", "Debre Tabor", "Burayu", "Adigrat", "Weldiya",
        "Shire Inda Selassie", "Bale Robe", "Boditi", "Butajira", "Gambela",
        "Harar", "Mizan Teferi", "Semera", "Bule Hora", "Welkite", "Wukro"
    ]

    job = Job.objects.get(id=id)
    all_skills = Skill.objects.all()  # 👈 fetch all skills
    job_categories = JobCategory.objects.all()

    if request.method == 'POST':
        job.title = request.POST.get('title')
        job.description = request.POST.get('description')
        job.category_id = request.POST.get('category')
        job.location = request.POST.get('location')
        job.job_type = request.POST.get('job_type')
        job.salary_range = request.POST.get('salary_range')
        job.deadline = request.POST.get('deadline')
        job.is_active = request.POST.get('is_active') == 'true'

        # 👈 update skills
        selected_skills = request.POST.getlist('required_skills')
        job.required_skills.set(selected_skills)

        job.save()
        return redirect('myjob')

    context = {
        'job': job,
        'job_cat': job_categories,
        'ethiopian_cities': ethiopian_cities,
        'all_skills': all_skills,  # 👈 pass skills to template
    }
    return render(request, 'job/edit_job.html', context)

@role_required('employer')
def delete_job(request,id):
    job = Job.objects.filter(id=id)
    job.delete()
    return redirect('myjob')
@role_required('employer')
def myjob(request):
    if not request.user.is_employer:
        return render(request, 'job/myjob.html', {'jobs': Job.objects.none(), 'all_jobs': []})
    
    all_jobs = Job.objects.filter(employer__user=request.user).order_by('-posted_on')  # For the dropdown

    # Filter for display
    jobs = all_jobs
    job_id = request.GET.get('job_id')
    if job_id:
        jobs = jobs.filter(id=job_id)

    context = {
        'jobs': jobs,          # Jobs to display
        'all_jobs': all_jobs,  # All jobs for dropdown
    }
    return render(request, 'job/myjob.html', context)
@role_required('employer')
def company_profile(request):
    employer_profile, created = EmployerProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
    # Update EmployerProfile fields
        employer_profile.comapany_name = request.POST.get('comapany_name', employer_profile.comapany_name)
        employer_profile.website = request.POST.get('website', employer_profile.website)
        employer_profile.About_company = request.POST.get('description', employer_profile.About_company)
        employer_profile.contact_phone = request.POST.get('phone', employer_profile.contact_phone)
        new_email = request.POST.get('email', employer_profile.contact_email)
        employer_profile.contact_email = new_email
        employer_profile.address = request.POST.get('address', employer_profile.address)
        employer_profile.linkedin_url = request.POST.get('linkedin', employer_profile.linkedin_url)
        employer_profile.twitter_url = request.POST.get('twitter', employer_profile.twitter_url)
        employer_profile.facebook_url = request.POST.get('facebook', employer_profile.facebook_url)

        # Handle logo upload
        if 'logo' in request.FILES:
            employer_profile.logo = request.FILES['logo']

        # Save EmployerProfile
        employer_profile.save()

        # Update User.email to match contact_email
        request.user.email = new_email
        request.user.save()

        # Redirect
        messages.success(request, "Profile updated successfully.")
        return redirect('employer_dashboard')# Replace with your URL name

    return render(request, 'job/company_profile.html', {'employer_profile': employer_profile})
@role_required('employer')
def post_jobs(request):
    for skill_name in skills:
        Skill.objects.get_or_create(name=skill_name)
    ethiopian_cities = [
        "Addis Ababa", "Mekelle", "Gondar", "Adama", "Bahir Dar", "Dire Dawa",
        "Hawassa", "Jimma", "Shashamane", "Bishoftu", "Sodo", "Arba Minch",
        "Jijiga", "Hosaena", "Kombolcha", "Dila", "Nekemte", "Debre Birhan",
        "Debre Markos", "Asella", "Debre Tabor", "Burayu", "Adigrat", "Weldiya",
        "Shire Inda Selassie", "Bale Robe", "Boditi", "Butajira", "Gambela",
        "Harar", "Mizan Teferi", "Semera", "Bule Hora", "Welkite", "Wukro"
    ]
    job_cat = JobCategory.objects.all()
    
    skills1 = Skill.objects.all()

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        category_id = request.POST.get('category')
        location = request.POST.get('location')
        job_type = request.POST.get('job_type')
        salary_range = request.POST.get('salary_range')
        deadline = request.POST.get('deadline')

        category = JobCategory.objects.get(id=category_id) if category_id else None
        employer, created = EmployerProfile.objects.get_or_create(user=request.user)

        job = Job.objects.create(
            employer=employer,
            title=title,
            description=description,
            category=category,
            location=location,
            job_type=job_type,
            salary_range=salary_range,
            deadline=deadline
        )

        selected_skills = request.POST.getlist("required_skills")
        if selected_skills:
            job.required_skills.set(selected_skills)

        messages.success(request, f"Job '{title}' successfully added.")
        return redirect('post_jobs')

    return render(request, 'job/post_jobs.html', {
        'job_cat': job_cat,
        'ethiopian_cities': ethiopian_cities,
        'skills': skills1
    })
def compaines(request):
    company_list = EmployerProfile.objects.all()
    context = {
        'company_list': company_list
    }
    return render(request, 'job/compaines.html', context)

def companies_homepage(request):
    companies = EmployerProfile.objects.all()
    context = {
        'companies': companies
    }
    return render(request, 'job/companies_homepage.html', context)
@role_required('job_seeker')
def apply_job(request, id):
    # Get the job object
    job = get_object_or_404(Job, id=id)

    # Get the job seeker profile if it exists
    seeker_profile = getattr(request.user, 'seekerprofile', None)

    # Check if the user already applied
    if JobApplication.objects.filter(job=job, applicant=request.user).exists():
        messages.warning(request, "You have already applied for this job.")
        return redirect('view_jobdetail', id=job.id)

    if request.method == 'POST':
        cover_letter = request.POST.get('cover_letter', '')

        # Check for uploaded resume
        if "resume" in request.FILES:
            resume_file = request.FILES['resume']
        else:
            # Use fallback resume from profile
            if seeker_profile and seeker_profile.resume:
                resume_file = seeker_profile.resume
            else:
                messages.error(request, "You must upload a resume to apply.")
                return redirect('apply_job', id=job.id)

        # Create the job application
        application = JobApplication.objects.create(
            job=job,
            applicant=request.user,
            cover_letter=cover_letter,
            resume=resume_file
        )

 

# Notification for the applicant (job seeker)
        Notification.objects.create(
    recipient=request.user,      # The seeker gets the notification
    actor=request.user,          # The action was performed by the seeker
    verb=f'You successfully applied to {job.title} at {job.employer.comapany_name}.',
    target=f'/myapplications/'   # Link to their applications
)
        Notification.objects.create(
    recipient=job.employer.user,      # The employer gets the notification
    actor=request.user,               # The action was performed by the seeker
    verb=f'Applied to your job: {job.title}',  # Short action description
    target=f'/view_applicants/{job.id}'  # Link to view applications
)
        # Send email notification to employer
        if job.employer.contact_email:
            try:
                send_mail(
                    subject="New Job Application Received",
                    message=f"{request.user.username} has test for your job: {job.title}.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[job.employer.contact_email],
                    fail_silently=False
                )
                print(f"Email sent to {job.employer.contact_email}")
            except Exception as e:
                # Print error to console for debugging
                print("Email sending failed:", e)

        messages.success(request, "Your application has been submitted successfully!")
        return redirect('myapplications')

    context = {'job': job}
    return render(request, 'job/apply_job.html', context)
@role_required('job_seeker')
def myapplications(request):
    if request.user.is_job_seeker:
        applications = JobApplication.objects.filter(applicant=request.user)
    else:
        applications = JobApplication.objects.none()
    context = {
        'applications': applications
    }
    return render(request, 'job/myapplications.html', context)

@role_required('employer')
def view_applicants(request, id):
    job = get_object_or_404(Job, id=id)
    
    # Get all applications with related seeker profile
    applications = JobApplication.objects.filter(job=job).select_related(
        'applicant', 'applicant__seekerprofile'
    ).order_by('-applied_on')
    
    # Job required skills
    job_skills = set(job.required_skills.values_list('id', flat=True)) if job.required_skills.exists() else set()

    # Calculate match score for each applicant
    for app in applications:
        seeker_skills = set(app.applicant.seekerprofile.skills.values_list('id', flat=True))
        if job_skills:
            matched = job_skills.intersection(seeker_skills)
            match_percent = round(len(matched) / len(job_skills) * 100)
        else:
            match_percent = 0

        app.match_score = match_percent
        app.missing_skills = list(job_skills - seeker_skills)

    # Filters
    status_filter = request.GET.get('status', 'all')
    if status_filter != 'all':
        applications = [a for a in applications if a.status == status_filter]

    search_query = request.GET.get('search', '')
    if search_query:
        applications = [
            a for a in applications if 
            search_query.lower() in a.applicant.username.lower() or
            search_query.lower() in a.applicant.email.lower() or
            (a.applicant.seekerprofile.first_name and search_query.lower() in a.applicant.seekerprofile.first_name.lower()) or
            (a.applicant.seekerprofile.last_name and search_query.lower() in a.applicant.seekerprofile.last_name.lower())
        ]

    # Sort by match score descending
    applications = sorted(applications, key=lambda x: x.match_score, reverse=True)

    # Statistics
    total_applications = len(applications)
    pending_applications = len([a for a in applications if a.status == 'applied'])
    accepted_applications = len([a for a in applications if a.status == 'accepted'])
    rejected_applications = len([a for a in applications if a.status == 'rejected'])
    reviewed_applications = len([a for a in applications if a.status == 'reviewed'])

    context = {
        'job': job,
        'applications': applications,
        'total_applications': total_applications,
        'pending_applications': pending_applications,
        'accepted_applications': accepted_applications,
        'rejected_applications': rejected_applications,
        'reviewed_applications': reviewed_applications,
        'status_filter': status_filter,
        'search_query': search_query,
        'employer_profile': getattr(request.user, 'employerprofile', None)
    }
    return render(request, 'job/view_applicants.html', context)


@role_required('job_seeker')
def my_resume(request):
    return render(request, 'job/my_resume.html')



def aboutus(request):   
    return render(request, 'job/aboutus.html')


from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings

def update_application_status(request, id):
    application = get_object_or_404(JobApplication, id=id)

    if request.method == 'POST':
        status = request.POST.get('status')
        if status in ['accepted', 'rejected']:
            # 1. Update status
            application.status = status
            application.save()

            # 2. Create in-app notification for the job seeker
            Notification.objects.create(
                recipient=application.applicant,
                actor=application.job.employer.user,
                verb=f"Your application was {status}.",
                target=application.job.title  # optional, can be blank or null
            )


            # 3. Determine recipient email (SeekerProfile email if exists)
            recipient_email = getattr(application.applicant, 'seekerprofile', None)
            if recipient_email and application.applicant.seekerprofile.email:
                recipient_email = application.applicant.seekerprofile.email
            else:
                recipient_email = application.applicant.email  # fallback

            # 4. Send email if email exists
            if recipient_email:
                if status == 'accepted':
                    subject = "Congratulations! Your Job Application is Accepted"
                    message = f"Dear {application.applicant.username},\n\n" \
                              f"Your application for '{application.job.title}' has been accepted. The employer will contact you with the next steps."
                elif status == 'rejected':
                    subject = "Job Application Update"
                    message = f"Dear {application.applicant.username},\n\n" \
                              f"We regret to inform you that your application for '{application.job.title}' was not successful."

                try:
                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[recipient_email],
                        fail_silently=False
                    )
                except Exception as e:
                    print(f"Failed to send email: {e}")

            messages.success(request, f"Application status updated to '{status}' and seeker notified.")

    return redirect('view_applicants', id=application.job.id)

@role_required('job_seeker')
def seeker_profile(request):
    ETHIOPIAN_CITIES = [
    "Addis Ababa", "Dire Dawa", "Mekelle", "Bahir Dar", "Hawassa", "Adama (Nazret)",
    "Jijiga", "Assosa", "Gambela", "Semera", "Nekemte", "Shashemene", "Dessie",
    "Gondar", "Lalibela", "Harar", "Jimma", "Dilla", "Wolaita Sodo", "Arba Minch",
    "Hosaena", "Debre Birhan", "Debre Markos", "Debre Tabor", "Axum", "Woldiya",
    "Kombolcha", "Bishoftu (Debre Zeit)", "Ambo", "Bale Robe", "Asella", "Bonga", "Tepi"
]
    user = request.user
    skills = Skill.objects.all()
    try:
        profile = SeekerProfile.objects.get(user=user)
    except SeekerProfile.DoesNotExist:
        profile = None

    if request.method == 'POST':
        if profile is None:
            # create profile only after submit
            profile = SeekerProfile(
                user=user,
                first_name=request.POST.get('first_name', '').strip(),
                last_name=request.POST.get('last_name', '').strip(),
                email=request.POST.get('email', '').strip(),
                phone_number=request.POST.get('phone_number', '').strip(),
                location=request.POST.get('location', '').strip(),
            )

            if 'resume' in request.FILES:
                profile.resume = request.FILES['resume']

            profile.save()

            selected_skills = request.POST.getlist('skills')
            profile.skills.set(selected_skills)
        else:
            # existing profile, update
            profile.first_name = request.POST.get('first_name', '').strip()
            profile.last_name = request.POST.get('last_name', '').strip()
            profile.email = request.POST.get('email', '').strip()
            profile.phone_number = request.POST.get('phone_number', '').strip()
            profile.location = request.POST.get('location', '').strip()

            if 'resume' in request.FILES:
                profile.resume = request.FILES['resume']

            profile.save()

            selected_skills = request.POST.getlist('skills')
            profile.skills.set(selected_skills)

        return redirect('seeker_profile')  # redirect after POST

    # GET request → render the form
    context = {
        'profile': profile,
        'skills': skills,
        'cities': ETHIOPIAN_CITIES,
    }
    return render(request, 'job/seeker_profile.html', context)
@role_required('admin')
def admin_home(request):
    
    return render(request, 'job/admin_home.html')
    return render(request, 'job/admin_dashboard.html')
@role_required('admin')

def admin_dashboard(request):
    # Total users
    total_users = User.objects.count()
    total_job_seekers = User.objects.filter(is_job_seeker=True).count()
    total_employers = User.objects.filter(is_employer=True).count()

    # Total jobs
    total_jobs = Job.objects.count()

    # Total applications
    total_applications = JobApplication.objects.count()

    # Accepted applications (Jobs filled)
    accepted_applications = JobApplication.objects.filter(status='accepted').count()

    # Calculate filled rate safely (avoid division by zero)
    filled_rate = (accepted_applications / total_jobs * 100) if total_jobs else 0

    # Recent activities (applications, job posts, new users)
    recent_applications = JobApplication.objects.select_related('applicant', 'job').order_by('-applied_on')[:5]
    recent_jobs = Job.objects.select_related('employer').order_by('-posted_on')[:5]
    recent_users = User.objects.order_by('-date_joined')[:5]

    # Chart data for applications per month
    current_year = now().year
    monthly_apps = (
        JobApplication.objects.filter(applied_on__year=current_year)
        .annotate(month=ExtractMonth('applied_on'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )

    applications_per_month = [0] * 12
    for entry in monthly_apps:
        applications_per_month[entry['month'] - 1] = entry['count']

    # Recent activities list
    recent_activities = []

    for app in recent_applications:
        recent_activities.append({
            'user': app.applicant.username,
            'activity': f"Applied for {app.job.title}",
            'time': app.applied_on,
        })

    for job in recent_jobs:
        recent_activities.append({
            'user': job.employer.user.username if hasattr(job.employer, 'user') else "Employer",
            'activity': f"Posted new job: {job.title}",
            'time': job.posted_on,
        })

    for u in recent_users:
        recent_activities.append({
            'user': u.username,
            'activity': "Created new account",
            'time': u.date_joined,
        })

    recent_activities = sorted(recent_activities, key=lambda x: x['time'], reverse=True)[:10]

    # Current date and month ranges
    today = now()
    start_current_month = today.replace(day=1)
    end_current_month = (today.replace(month=today.month + 1, day=1) - datetime.timedelta(seconds=1)
                         if today.month < 12 else today.replace(year=today.year + 1, month=1, day=1) - datetime.timedelta(seconds=1))

    jobs_current_month = Job.objects.filter(posted_on__range=(start_current_month, end_current_month)).count()
    apps_current_month = JobApplication.objects.filter(applied_on__range=(start_current_month, end_current_month)).count()

    # Previous month range
    if today.month == 1:
        previous_month_start = today.replace(year=today.year - 1, month=12, day=1)
        previous_month_end = today.replace(year=today.year - 1, month=12, day=31)
    else:
        previous_month_start = today.replace(month=today.month - 1, day=1)
        previous_month_end = today.replace(day=1) - datetime.timedelta(seconds=1)

    jobs_previous_month = Job.objects.filter(posted_on__range=(previous_month_start, previous_month_end)).count()
    apps_previous_month = JobApplication.objects.filter(applied_on__range=(previous_month_start, previous_month_end)).count()

    # Percentage change safely
    jobs_change = ((jobs_current_month - jobs_previous_month) / jobs_previous_month * 100) if jobs_previous_month else 0
    applications_change = ((apps_current_month - apps_previous_month) / apps_previous_month * 100) if apps_previous_month else 0

    context = {
        'total_users': total_users,
        'total_job_seekers': total_job_seekers,
        'total_employers': total_employers,
        'total_jobs': total_jobs,
        'total_applications': total_applications,
        'accepted_applications': accepted_applications,
        'filled_rate': round(filled_rate, 1),
        'recent_activities': recent_activities,
        'applications_per_month': applications_per_month,
        'jobs_change': round(jobs_change, 1),
        'applications_change': round(applications_change, 1),
    }

    return render(request, 'job/admin_dashboard.html', context)
def job_applied_show_admin(request):
    applications = JobApplication.objects.all().select_related('job', 'applicant')
    context = {
        'applications': applications
    }
    return render(request, 'job/job_applied_show_admin.html', context)

@role_required('admin')
def delete_job_applications(request, id):
    application = get_object_or_404(JobApplication, id=id)
    job_id = application.job.id 
    application.delete()
    messages.success(request, "Job application deleted successfully.")
    return redirect('job_applied_show_admin')
@role_required('admin')
def active_jobs(request):
    active = Job.objects.filter(deadline__gte=timezone.now().date())
    context = {
        'active_jobs': active
    }
    return render(request, 'job/active_jobs.html', context)
@role_required('admin')
def expired_jobs(request):
    expired = Job.objects.filter(deadline__lt=timezone.now().date())
    context = {
        'expired': expired
    }
    return render(request, 'job/expired_jobs.html', context)
@role_required('job_seeker')
def saved_jobs(request):
    saved_jobs_list = SavedJob.objects.all()
    context = {
        'saved_jobs': saved_jobs_list
    }
    return render(request, 'job/saved_jobs.html', context)
    


def toggle_save_job(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    saved_job, created = SavedJob.objects.get_or_create(user=request.user, job=job)

    if not created:
        # Already exists → unsave
        saved_job.delete()

    return redirect(request.META.get('HTTP_REFERER', '/'))


def company_job_list(request, id):
    company = get_object_or_404(EmployerProfile, id=id)
    jobs = Job.objects.filter(employer=company).order_by('-posted_on')

    # Pagination (optional, 9 jobs per page)
    paginator = Paginator(jobs, 9)
    page_number = request.GET.get('page')
    jobs_page = paginator.get_page(page_number)
    context = {
        'company': company,
        'jobs': jobs_page,
        'total_jobs': jobs.count(),
    }

    return render(request, 'job/company_job_list.html', context)


def notification_redirect(request, id):
    notification = get_object_or_404(Notification, id=id, recipient=request.user)
    notification.is_read = True
    notification.save()
    # Redirect user to relevant page, e.g., job detail
    return redirect('view_jobdetail', id=notification.target_id)  # You may need target_id in Notification
@role_required('job_seeker')
def edit_seeker_profile(request, id):
    seeker_profile = request.user.seekerprofile

    if request.method == 'POST':
        # Only update fields if new data is provided
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        skills = request.POST.get('skills')
        experience = request.POST.get('experience')
        resume = request.FILES.get('resume')

        if first_name:
            seeker_profile.first_name = first_name
        if last_name:
            seeker_profile.last_name = last_name
        if email:
        # Update both SeekerProfile and default User email
            seeker_profile.email = email
            request.user.email = email
            request.user.save()
        if phone_number:
            seeker_profile.phone_number = phone_number
        if skills:
            seeker_profile.skills = skills
        if experience:
            seeker_profile.experience = experience
        if resume:
            seeker_profile.resume = resume

        seeker_profile.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('seeker_profile')

    context = {'seeker_profile': seeker_profile}
    return render(request, 'job/edit_seeker_profile.html', context)


@role_required('employer')
def view_application(request, id):
    application = get_object_or_404(JobApplication, id=id)

    if request.method == "POST":
        new_status = request.POST.get("status")
        if new_status in ["applied", "reviewed", "interview", "accepted", "rejected"]:
            application.status = new_status
            application.save()
            return redirect("employer_dashboard")  # redirect back after update

    context = {
        "application": application,
    }
    return render(request, "job/view_application.html", context)


@login_required
@user_passes_test(lambda u: u.is_superuser)  # Only admin can delete
def delete_user(request, id):
    user = get_object_or_404(User, id=id)
    if not user.is_superuser:
        user.delete()
        messages.success(request, f"User {user.username} deleted successfully.")
    else:
        messages.error(request, "Cannot delete superuser!")
    return redirect('userlist')  # Replace with your user list URL name

def notifications_view(request):
    # Fetch notifications for the logged-in user
    notifications = Notification2.objects.filter(user=request.user)
    return render(request, 'job/notifications.html', {'notifications': notifications})

def mark_notification_read(request, pk):
    # Mark the notification as read
    notif = Notification.objects.get(pk=pk, user=request.user)
    notif.is_read = True
    notif.save()
    # Redirect to the notification's link if it exists, else to notifications page
    return redirect(notif.link or 'notifications')
def mark_all_notifications_read_ajax(request):
    if request.user.is_authenticated and request.method == "POST":
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return JsonResponse({'success': True, 'notif_count': 0})
    return JsonResponse({'success': False}, status=400)


def mark_notification_read(request, pk):
    # Get the notification for the logged-in user
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
    
    # Mark it as read
    notif.is_read = True
    notif.save()
    
    # Redirect to the target URL (or a default page)
    return redirect(notif.target or 'notifications')  #
def withdraw_application(request, app_id):
    if not request.user.is_authenticated:
        messages.error(request, "You must be logged in to withdraw an application.")
        return redirect('login')

    application = get_object_or_404(JobApplication, id=app_id, applicant=request.user)

    # Only allow withdrawal if still applied
    if application.status != 'applied':
        messages.warning(request, "You cannot withdraw this application at this stage.")
        return redirect('my_applications')

    application.status = 'withdrawn'
    application.save()
    messages.success(request, f"You have successfully withdrawn your application for {application.job.title}.")
    return redirect('myapplications')