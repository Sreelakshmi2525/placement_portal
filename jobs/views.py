# jobs/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import datetime
from .models import Job, Department, JobApplication, Assessment, AssessmentResponse, Question, Option, Skill, ExternalJobApplication, EmailTemplate,EmailLog
from .forms import JobForm, JobScrapeForm, EmailTemplate, EmailForm, EmailTemplateForm
from users.models import User
import jobspy  
import os
from django.core.files.storage import FileSystemStorage
from functools import wraps
from .ml_utils import extract_text_from_resume, match_resume_to_job
from .job_application_bot import JobApplicationBot
from django.conf import settings
from django.http import JsonResponse 
import fitz  # PyMuPDF


def plo_required(view_func):
    """Decorator to verify the user is a placement officer"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_placement_officer():
            messages.error(request, "You don't have permission to access this page.")
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper

@login_required
@plo_required
def job_list(request):
    jobs = Job.objects.all()
    return render(request, 'jobs/job_list.html', {'jobs': jobs})

@login_required
@plo_required
def job_detail(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    return render(request, 'jobs/job_detail.html', {'job': job})

@login_required
@plo_required
def job_create(request):
    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.created_by = request.user
            job.save()
            # Save many-to-many relationships
            form.save_m2m()
            messages.success(request, 'Job posting created successfully.')
            return redirect('job_list')
    else:
        form = JobForm()
    
    return render(request, 'jobs/job_form.html', {'form': form})

@login_required
@plo_required
def job_edit(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    if request.method == 'POST':
        form = JobForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            messages.success(request, 'Job posting updated successfully.')
            return redirect('job_list')
    else:
        form = JobForm(instance=job)
    
    return render(request, 'jobs/job_form.html', {'form': form, 'job': job})

@login_required
@plo_required
def job_delete(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    if request.method == 'POST':
        job.delete()
        messages.success(request, 'Job posting deleted successfully.')
        return redirect('job_list')
    
    return render(request, 'jobs/job_confirm_delete.html', {'job': job})
def user_can_scrape(user):
    """Check if the user has permission to scrape jobs."""
    # Allow both students and placement officers to scrape
    return user.is_authenticated and (user.is_student() or user.is_placement_officer())
@login_required
def job_scrape(request):
    if not user_can_scrape(request.user):
        messages.error(request, "You don't have permission to use this feature.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = JobScrapeForm(request.POST)
        if form.is_valid():
            keyword = form.cleaned_data['keyword']
            location = form.cleaned_data['location']
            limit = form.cleaned_data['limit']
            
            try:
                # Use our custom LinkedIn scraper
                from .job_scraper import LinkedInJobScraper
                
                scraper = LinkedInJobScraper()
                if not scraper.driver:
                    # If driver failed to initialize, show an error
                    messages.error(request, "Failed to initialize the web driver. Please make sure Chrome is installed.")
                    return render(request, 'jobs/job_scrape.html', {'form': form})
                
                try:
                    # Login to LinkedIn
                    login_success = scraper.login()
                    if not login_success:
                        messages.warning(request, "Login to LinkedIn failed. Using basic search without login.")
                    
                    # Get jobs
                    scraped_jobs = scraper.get_jobs(keywords=keyword, location=location, max_jobs=limit)
                    
                    # Always close the browser
                    scraper.close()
                    
                    if not scraped_jobs:
                        messages.warning(request, f"No jobs found for '{keyword}' in '{location}'. Try different search terms.")
                        return render(request, 'jobs/job_scrape.html', {'form': form})
                    is_student = request.user.is_student()
                    return render(request, 'jobs/job_scrape_results.html', {

                        'scraped_jobs': scraped_jobs,
                        'is_student': is_student 
                    })
                    
                finally:
                    # Ensure browser is closed even if an exception occurs
                    scraper.close()
                
            except Exception as e:
                import traceback
                print(f"Error scraping jobs: {str(e)}")
                print(traceback.format_exc())
                messages.error(request, f'Error scraping jobs: {str(e)}')
                return render(request, 'jobs/job_scrape.html', {'form': form})
    else:
        form = JobScrapeForm()
    
    return render(request, 'jobs/job_scrape.html', {'form': form})

@login_required
def save_scraped_job(request):
    # Check if user has permission
    if not user_can_scrape(request.user):
        messages.error(request, "You don't have permission to use this feature.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        # Extract job data from the POST request
        title = request.POST.get('title', '')
        company = request.POST.get('company', '')
        location = request.POST.get('location', '')
        description = request.POST.get('description', '')
        salary = request.POST.get('salary', '')
        url = request.POST.get('url', '')
        
        # Validate the required fields
        if not title or not company:
            messages.error(request, 'Title and company are required.')
            return redirect('job_scrape')
        
        if request.user.is_placement_officer():
            # PLOs can save jobs to the database
            try:
                job = Job(
                    title=title,
                    company=company,
                    location=location,
                    description=description,
                    requirements="Requirements extracted from job description.",
                    salary=salary,
                    url=url,
                    created_by=request.user,
                    status='active'
                )
                job.save()
                
                messages.success(request, 'Job saved successfully.')
                return redirect('job_list')
            except Exception as e:
                messages.error(request, f'Error saving job: {str(e)}')
                return redirect('job_scrape')
        else:
            # Students can apply directly to the external job
            # Just redirect them to the job URL
            messages.info(request, 'Redirecting you to the job posting.')
            return redirect(url)
    
    return redirect('job_scrape')

@login_required
@plo_required
def assign_departments(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    departments = Department.objects.all()
    
    if request.method == 'POST':
        selected_departments = request.POST.getlist('departments')
        job.departments.clear()
        for dept_id in selected_departments:
            department = Department.objects.get(id=dept_id)
            job.departments.add(department)
        
        messages.success(request, 'Departments assigned successfully.')
        return redirect('job_detail', job_id=job.id)
    
    return render(request, 'jobs/assign_departments.html', {
        'job': job,
        'departments': departments
    })

@login_required
@plo_required
def department_list(request):
    departments = Department.objects.all()
    return render(request, 'jobs/department_list.html', {'departments': departments})

@login_required
@plo_required
def department_create(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            Department.objects.create(name=name)
            messages.success(request, 'Department created successfully.')
            return redirect('department_list')
        else:
            messages.error(request, 'Department name is required.')
    
    return render(request, 'jobs/department_form.html')

@login_required
@plo_required
def department_edit(request, dept_id):
    department = get_object_or_404(Department, id=dept_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            department.name = name
            department.save()
            messages.success(request, 'Department updated successfully.')
            return redirect('department_list')
        else:
            messages.error(request, 'Department name is required.')
    
    return render(request, 'jobs/department_form.html', {'department': department})

@login_required
@plo_required
def department_delete(request, dept_id):
    department = get_object_or_404(Department, id=dept_id)
    
    if request.method == 'POST':
        department.delete()
        messages.success(request, 'Department deleted successfully.')
        return redirect('department_list')
    
    return render(request, 'jobs/department_confirm_delete.html', {'department': department})

@login_required
@plo_required
def department_jobs(request, dept_id):
    department = get_object_or_404(Department, id=dept_id)
    jobs = department.jobs.all()
    
    return render(request, 'jobs/department_jobs.html', {
        'department': department,
        'jobs': jobs
    })

def student_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_student():
            return view_func(request, *args, **kwargs)
        return redirect('login')
    return _wrapped_view

@login_required
@student_required
@login_required
@student_required
def student_job_list(request):
    student = request.user.student_profile
    
    # Get all active jobs
    jobs = Job.objects.filter(status='active')
    
    # If department is properly set up as a ForeignKey to Department
    if hasattr(student, 'department') and student.department:
        # Check if department is an actual Department instance or just a string
        if isinstance(student.department, str):
            # If it's a string, try to find departments with matching names
            department_jobs = jobs.filter(departments__name__icontains=student.department)
            general_jobs = jobs.filter(departments__isnull=True)
            jobs = (department_jobs | general_jobs).distinct()
        else:
            # If it's a proper Department instance, filter by the department ID
            department_jobs = jobs.filter(departments=student.department)
            general_jobs = jobs.filter(departments__isnull=True)
            jobs = (department_jobs | general_jobs).distinct()
    
    # Get jobs the student has already applied for
    applied_jobs = []
    if hasattr(student, 'applications'):
        applied_jobs = student.applications.values_list('job_id', flat=True)
    
    return render(request, 'jobs/student_job_list.html', {
        'jobs': jobs,
        'applied_jobs': applied_jobs,
    })

@login_required
@student_required
def apply_for_job(request, job_id):
    job = get_object_or_404(Job, id=job_id, status='active')
    student = request.user.student_profile
    
    # Check if already applied
    if JobApplication.objects.filter(job=job, student=student).exists():
        messages.warning(request, "You have already applied for this job.")
        return redirect('student_job_detail', job_id=job.id)
    
    if request.method == 'POST':
        cover_letter = request.POST.get('cover_letter', '')
        
        # Create application
        JobApplication.objects.create(
            job=job,
            student=student,
            cover_letter=cover_letter,
            status='applied'
        )
        
        messages.success(request, "Your application has been submitted successfully!")
        return redirect('my_applications')
    
    return render(request, 'jobs/apply_for_job.html', {
        'job': job,
    })
# jobs/views.py
@login_required
@student_required
def my_applications(request):
    student = request.user.student_profile
    
    # Get internal applications
    internal_applications = JobApplication.objects.filter(student=student).order_by('-applied_date')
    
    # Debug information
    print(f"Student: {student.user.username}")
    print(f"Internal applications found: {internal_applications.count()}")
    for app in internal_applications:
        print(f"Application: {app.job.title} at {app.job.company}, status: {app.status}")
    
    # Check if there are any external applications
    has_external_apps = hasattr(ExternalJobApplication, 'objects')
    external_applications = []
    
    if has_external_apps:
        external_applications = ExternalJobApplication.objects.filter(student=student).order_by('-application_date')
        print(f"External applications found: {external_applications.count()}")
    
    return render(request, 'jobs/my_applications.html', {
        'internal_applications': internal_applications,
        'external_applications': external_applications,
        'has_external_apps': has_external_apps,
    })
from sentence_transformers import SentenceTransformer, util
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Load a sentence transformer model (you can fine-tune your own on job data for "JobBERT")
model = SentenceTransformer('all-MiniLM-L6-v2')

def extract_text_from_resume(resume_path):
    try:
        doc = fitz.open(resume_path)
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        print(f"Error extracting resume: {e}")
        return None

# Load a lightweight sentence transformer model
model = SentenceTransformer('all-MiniLM-L6-v2')

def match_resume_to_job(resume_text, job_description, job_requirements):
    # Combine job info into one text block
    job_text = job_description + " " + " ".join(job_requirements)

    # Get sentence embeddings
    resume_embedding = model.encode(resume_text, convert_to_tensor=True)
    job_embedding = model.encode(job_text, convert_to_tensor=True)

    # Compute cosine similarity
    similarity = util.cos_sim(resume_embedding, job_embedding).item()
    score = int(similarity * 100)

    # Find missing skills (simple keyword matching)
    resume_lower = resume_text.lower()
    missing_skills = [skill for skill in job_requirements if skill.lower() not in resume_lower]

    return score, missing_skills
def predict_job_success(student, job):
    """
    Predict job success by semantic matching of resume to job description and requirements,
    and return missing skills.
    """
    if not student.resume:
        return None, []
    else:
        resume_path = os.path.join(settings.MEDIA_ROOT, str(student.resume))

    # TODO: Change to dynamic path in production
    resume_text = extract_text_from_resume(str(resume_path))

    if not resume_text:
        print("No resume text extracted.")
        return None, []

    # Perform semantic matching and find missing skills
    match_score, missing_skills = match_resume_to_job(
        resume_text,
        job.description,
        job.requirements
    )

    return match_score, missing_skills
# jobs/views.py
@login_required
@student_required
def student_job_detail(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    student = request.user.student_profile
    
    # Check if student has already applied
    already_applied = JobApplication.objects.filter(job=job, student=student).exists()
    
    # Calculate job match score if resume is uploaded
    job_match_score = None
    missing_skills = []
    
    if student.resume:
        job_match_score, missing_skills = predict_job_success(student, job)
    
    return render(request, 'jobs/student_job_detail.html', {
        'job': job,
        'already_applied': already_applied,
        'job_match_score': job_match_score,
        'missing_skills': missing_skills,
    })
@login_required
@student_required
def resume_upload(request):
    student = request.user.student_profile
    
    if request.method == 'POST' and request.FILES.get('resume'):
        resume_file = request.FILES['resume']
        
        # Check file extension
        file_ext = os.path.splitext(resume_file.name)[1].lower()
        if file_ext not in ['.pdf', '.docx', '.doc']:
            messages.error(request, "Please upload a PDF or Word document (.pdf, .docx, .doc)")
            return redirect('resume_upload')
        
        # Save the file
        student.resume = resume_file
        student.save()
        
        messages.success(request, "Resume uploaded successfully! We'll analyze it to help match you with jobs.")
        return redirect('dashboard')
    
    return render(request, 'jobs/resume_upload.html', {
        'student': student
    })
from .services import QuestionGenerationService

@login_required
@student_required
def take_assessment(request):
    student = request.user.student_profile
    
    if request.method == 'POST':
        job_type = request.POST.get('job_type')
        
        # Create a new assessment
        assessment = Assessment.objects.create(
            student=student,
            job_type=job_type
        )
        
        # Redirect to the assessment questions
        return redirect('assessment_questions', assessment_id=assessment.id)
    
    # Job types available for assessment
    job_types = ["developer", "designer", "analyst", "manager", "data_scientist"]
    
    return render(request, 'jobs/take_assessment.html', {
        'job_types': job_types
    })

@login_required
@student_required
def assessment_questions(request, assessment_id):
    assessment = get_object_or_404(Assessment, id=assessment_id, student=request.user.student_profile)
    
    # Check if we have questions for this assessment in the database
    questions = Question.objects.filter(job_type=assessment.job_type)
    
    # If not enough questions, generate them using ML
    if questions.count() < 3:
        questions = generate_and_save_questions(assessment.job_type)
    
    if request.method == 'POST':
        # Process responses
        for question in questions:
            if question.question_type == 'mcq':
                option_id = request.POST.get(f'question_{question.id}')
                if option_id:
                    option = Option.objects.get(id=option_id)
                    AssessmentResponse.objects.create(
                        assessment=assessment,
                        question=question,
                        selected_option=option
                    )
            elif question.question_type == 'rating':
                rating = request.POST.get(f'question_{question.id}')
                if rating:
                    AssessmentResponse.objects.create(
                        assessment=assessment,
                        question=question,
                        rating_response=int(rating)
                    )
        
        # Generate skill recommendations
        return redirect('assessment_results', assessment_id=assessment.id)
    
    return render(request, 'jobs/assessment_questions.html', {
        'assessment': assessment,
        'questions': questions
    })

def generate_and_save_questions(job_type):
    """Generate questions using ML API and save to database"""
    service = QuestionGenerationService()
    questions_data = service.generate_questions(job_type)
    
    saved_questions = []
    
    for q_data in questions_data:
        # Create the question
        question = Question.objects.create(
            text=q_data['text'],
            question_type=q_data['type'],
            job_type=job_type
        )
        
        # Create options for MCQ questions
        if q_data['type'] == 'mcq' and 'options' in q_data:
            for opt_data in q_data['options']:
                option = Option.objects.create(
                    question=question,
                    text=opt_data['text']
                )
                
                # Add skills to the option
                if 'skills' in opt_data:
                    for skill_name in opt_data['skills']:
                        skill, _ = Skill.objects.get_or_create(name=skill_name)
                        option.skills.add(skill)
        
        saved_questions.append(question)
    
    return saved_questions

@login_required
@student_required
def assessment_results(request, assessment_id):
    assessment = get_object_or_404(Assessment, id=assessment_id, student=request.user.student_profile)
    
    # Analyze responses and generate skill recommendations
    recommended_skills = generate_skill_recommendations(assessment)
    
    # Calculate percentages for the template
    for skill in recommended_skills:
        skill['percentage'] = min((skill['score'] * 20) + 20, 100)  # Scale to percentage
    
    return render(request, 'jobs/assessment_results.html', {
        'assessment': assessment,
        'recommended_skills': recommended_skills
    })

def generate_skill_recommendations(assessment):
    """
    Generate skill recommendations based on assessment responses
    """
    # Get all responses for this assessment
    responses = assessment.responses.all()
    
    # Collect skills from selected options
    skill_count = {}
    for response in responses:
        if response.selected_option:
            for skill in response.selected_option.skills.all():
                if skill.name in skill_count:
                    skill_count[skill.name] += 1
                else:
                    skill_count[skill.name] = 1
    
    # If we don't have enough skills from responses, use ML to suggest more
    if len(skill_count) < 3:
        additional_skills = suggest_additional_skills(assessment.job_type)
        for skill in additional_skills:
            if skill not in skill_count:
                skill_count[skill] = 1
    
    # Convert to list of dictionaries
    recommended_skills = [
        {"name": skill, "score": count} 
        for skill, count in sorted(skill_count.items(), key=lambda x: x[1], reverse=True)
    ]
    
    return recommended_skills[:6]  # Return top 6 skills

def suggest_additional_skills(job_type):
    """Use ML to suggest additional skills for a job type"""
    job_specific_skills = {
        "developer": ["JavaScript", "Python", "Git", "React", "Node.js", "Docker"],
        "designer": ["UI/UX", "Figma", "Adobe Creative Suite", "Typography", "Color Theory"],
        "analyst": ["SQL", "Excel", "Tableau", "Power BI", "Statistical Analysis", "Python"],
        "manager": ["Project Management", "Agile", "Team Leadership", "Stakeholder Communication"],
        "data_scientist": ["Python", "R", "Machine Learning", "Statistics", "Data Visualization", "Big Data"]
    }
    
    return job_specific_skills.get(job_type, [])[:3]

# jobs/views.py
# Add this view for automated job applications

@login_required
@student_required
def auto_apply_to_job(request, job_id=None):
    """Automatically apply to a job using the application bot."""
    job = None
    job_url = request.POST.get('job_url', '')
    
    # Get job from our database if job_id is provided
    if job_id:
        job = get_object_or_404(Job, id=job_id)
        job_url = job.url
    
    # Make sure we have a job URL
    if not job_url:
        messages.error(request, "No job URL provided.")
        return redirect('student_job_list')
    
    # Get student info
    student = request.user.student_profile
    resume_path = ""
    
    # If student has a resume, get its path
    if student.resume:
        resume_path = os.path.join(settings.MEDIA_ROOT, str(student.resume))
        if not os.path.exists(resume_path):
            messages.warning(request, "Your resume file could not be found. Please re-upload it.")
            resume_path = ""
    else:
        messages.warning(request, "You don't have a resume uploaded. The application might not be complete.")
    
    # Prepare student info for the bot
    student_info = {
        'name': f"{request.user.first_name} {request.user.last_name}",
        'email': request.user.email,
        'phone': getattr(student, 'phone', ''),  # Assuming you have a phone field
        'resume_path': resume_path
    }
    
    # Initialize and run the application bot
    try:
        application_bot = JobApplicationBot()
        if not application_bot.driver:
            messages.error(request, "Could not initialize the application bot. Please try again later.")
            return redirect('student_job_list')
        
        try:
            # Login and apply
            login_success = application_bot.login_to_linkedin()
            if not login_success:
                messages.error(request, "Failed to log in to LinkedIn. Please try again later.")
                return redirect('student_job_list')
            
            success, status_message = application_bot.apply_to_job(job_url, student_info)
            
            # Create a record of the application
            if success:
                if job:
                    # If it's a job from our database, create a formal application
                    existing_application = JobApplication.objects.filter(job=job, student=student).exists()
                    if not existing_application:
                        JobApplication.objects.create(
                            job=job,
                            student=student,
                            status='applied',
                            cover_letter=f"Applied automatically via LinkedIn on {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                        )
                
                # Create a record for external applications too
                ExternalJobApplication.objects.create(
                    student=student,
                    job_title=job.title if job else "LinkedIn Job",
                    company=job.company if job else "Unknown",
                    application_date=datetime.now(),
                    job_url=job_url,
                    status='applied',
                    application_method='bot',
                    notes=status_message
                )
                
                messages.success(request, f"Application process completed: {status_message}")
            else:
                messages.error(request, f"Application failed: {status_message}")
            
            return redirect('my_applications')
        
        finally:
            # Make sure we always close the browser
            application_bot.close()
    
    except Exception as e:
        messages.error(request, f"Error during application: {str(e)}")
        return redirect('student_job_list')

# jobs/views.py
# Email template management views
@login_required
@plo_required
def email_template_list(request):
    templates = EmailTemplate.objects.filter(created_by=request.user)
    return render(request, 'jobs/email_template_list.html', {
        'templates': templates
    })

@login_required
@plo_required
def email_template_create(request):
    if request.method == 'POST':
        form = EmailTemplateForm(request.POST)
        if form.is_valid():
            template = form.save(commit=False)
            template.created_by = request.user
            template.save()
            messages.success(request, 'Email template created successfully.')
            return redirect('email_template_list')
    else:
        form = EmailTemplateForm()
    
    return render(request, 'jobs/email_template_form.html', {
        'form': form
    })

@login_required
@plo_required
def email_template_edit(request, template_id):
    template = get_object_or_404(EmailTemplate, id=template_id, created_by=request.user)
    
    if request.method == 'POST':
        form = EmailTemplateForm(request.POST, instance=template)
        if form.is_valid():
            form.save()
            messages.success(request, 'Email template updated successfully.')
            return redirect('email_template_list')
    else:
        form = EmailTemplateForm(instance=template)
    
    return render(request, 'jobs/email_template_form.html', {
        'form': form,
        'template': template
    })

@login_required
@plo_required
def email_template_delete(request, template_id):
    template = get_object_or_404(EmailTemplate, id=template_id, created_by=request.user)
    
    if request.method == 'POST':
        template.delete()
        messages.success(request, 'Email template deleted successfully.')
        return redirect('email_template_list')
    
    return render(request, 'jobs/email_template_confirm_delete.html', {
        'template': template
    })

# Email sending views
@login_required
@plo_required
def send_email(request, job_id=None):
    job = None
    if job_id:
        job = get_object_or_404(Job, id=job_id)
    
    if request.method == 'POST':
        form = EmailForm(request.POST, user=request.user)
        if form.is_valid():
            recipient = form.cleaned_data['recipient']
            cc = form.cleaned_data['cc']
            subject = form.cleaned_data['subject']
            content = form.cleaned_data['content']
            
            try:
                # Send email using Django's email functionality
                from django.core.mail import EmailMessage
                
                email = EmailMessage(
                    subject=subject,
                    body=content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[recipient],
                    cc=[cc] if cc else []
                )
                email.send(fail_silently=False)
                
                # Log the email
                EmailLog.objects.create(
                    subject=subject,
                    recipient=recipient,
                    content=content,
                    sent_by=request.user,
                    job=job
                )
                
                messages.success(request, f'Email sent successfully to {recipient}.')
                
                # Redirect appropriately
                if job:
                    return redirect('job_detail', job_id=job.id)
                else:
                    return redirect('email_log')
                
            except Exception as e:
                messages.error(request, f'Error sending email: {str(e)}')
    else:
        initial_data = {}
        
        # If there's a job, pre-populate the form with job information
        if job:
            company_email = ""  # You might want to add a company email field to the Job model
            initial_data = {
                'recipient': company_email,
                'subject': f"Regarding {job.title} position at {job.company}",
                'content': f"""Dear Hiring Manager,

I'm writing on behalf of {settings.INSTITUTION_NAME}, regarding the {job.title} position at {job.company}.

We have several qualified students who would be excellent candidates for this role. I would like to discuss how we can connect our students with this opportunity.

Please let me know a convenient time to discuss this further.

Best regards,
{request.user.get_full_name()}
Placement Officer
{settings.INSTITUTION_NAME}
"""
            }
        
        form = EmailForm(initial=initial_data, user=request.user)
    
    return render(request, 'jobs/send_email.html', {
        'form': form,
        'job': job
    })

@login_required
@plo_required
def email_log(request):
    emails = EmailLog.objects.filter(sent_by=request.user).order_by('-sent_at')
    return render(request, 'jobs/email_log.html', {
        'emails': emails
    })

@login_required
@plo_required
def get_template_content(request, template_id):
    """AJAX view to get template content"""
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            template = get_object_or_404(EmailTemplate, id=template_id, created_by=request.user)
            return JsonResponse({
                'subject': template.subject,
                'content': template.content
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid request'}, status=400)

# jobs/views.py
@login_required
@plo_required
def application_list(request):
    # Get all applications
    applications = JobApplication.objects.all().order_by('-applied_date')
    
    # Filter by job if specified
    job_id = request.GET.get('job')
    if job_id:
        applications = applications.filter(job_id=job_id)
    
    # Filter by status if specified
    status = request.GET.get('status')
    if status:
        applications = applications.filter(status=status)
    
    # Get all jobs for the filter dropdown
    jobs = Job.objects.all()
    
    return render(request, 'jobs/application_list.html', {
        'applications': applications,
        'jobs': jobs,
        'current_job_filter': job_id,
        'current_status_filter': status,
        'STATUS_CHOICES': JobApplication.STATUS_CHOICES
    })

# jobs/views.py
@login_required
@plo_required
def view_application(request, application_id):
    application = get_object_or_404(JobApplication, id=application_id)
    
    return render(request, 'jobs/view_application.html', {
        'application': application
    })

@login_required
@plo_required
def update_application_status(request, application_id):
    application = get_object_or_404(JobApplication, id=application_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(JobApplication.STATUS_CHOICES):
            application.status = new_status
            application.save()
            messages.success(request, f"Application status updated to '{dict(JobApplication.STATUS_CHOICES)[new_status]}'.")
        else:
            messages.error(request, "Invalid status provided.")
    
    return redirect('application_list')