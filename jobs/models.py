# jobs/models.py
from django.db import models
from users.models import User

class Department(models.Model):
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name

class Job(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('closed', 'Closed'),
        ('pending', 'Pending Review'),
    )
    
    title = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    description = models.TextField()
    requirements = models.TextField()
    location = models.CharField(max_length=200)
    salary = models.CharField(max_length=100, blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    departments = models.ManyToManyField(Department, related_name='jobs', blank=True)
    date_posted = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_jobs')
    
    def __str__(self):
        return f"{self.title} at {self.company}"
    
    class Meta:
        ordering = ['-date_posted']

# jobs/models.py
class JobApplication(models.Model):
    STATUS_CHOICES = (
        ('applied', 'Applied'),
        ('under_review', 'Under Review'),
        ('shortlisted', 'Shortlisted'),
        ('rejected', 'Rejected'),
        ('selected', 'Selected'),
    )
    
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    student = models.ForeignKey('users.StudentProfile', on_delete=models.CASCADE, related_name='applications')
    applied_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='applied')
    cover_letter = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ('job', 'student')
        
    def __str__(self):
        return f"{self.student.user.username} - {self.job.title}"

class Skill(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.name

class Question(models.Model):
    QUESTION_TYPES = (
        ('mcq', 'Multiple Choice'),
        ('rating', 'Rating Scale'),
    )
    
    text = models.TextField()
    question_type = models.CharField(max_length=6, choices=QUESTION_TYPES)
    job_type = models.CharField(max_length=100)  # e.g., "developer", "designer"
    
    def __str__(self):
        return self.text[:50]

class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    text = models.CharField(max_length=200)
    skills = models.ManyToManyField(Skill, blank=True, related_name='options')
    
    def __str__(self):
        return self.text

class Assessment(models.Model):
    student = models.ForeignKey('users.StudentProfile', on_delete=models.CASCADE, related_name='assessments')
    job_type = models.CharField(max_length=100)
    date_taken = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.student.user.username} - {self.job_type} assessment"

class AssessmentResponse(models.Model):
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='responses')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.ForeignKey(Option, on_delete=models.CASCADE, null=True, blank=True)
    rating_response = models.IntegerField(null=True, blank=True)
    
    class Meta:
        unique_together = ('assessment', 'question')

# jobs/models.py
# Add this model for tracking external job applications

class ExternalJobApplication(models.Model):
    student = models.ForeignKey('users.StudentProfile', on_delete=models.CASCADE, related_name='external_applications')
    job_title = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    application_date = models.DateTimeField(auto_now_add=True)
    job_url = models.URLField()
    status = models.CharField(max_length=50, default='applied')
    application_method = models.CharField(max_length=50, default='manual')
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.student.user.username} - {self.job_title} at {self.company}"

# jobs/models.py
# Add this model for email templates
class EmailTemplate(models.Model):
    name = models.CharField(max_length=100)
    subject = models.CharField(max_length=200)
    content = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

# Add this model to track sent emails
class EmailLog(models.Model):
    subject = models.CharField(max_length=200)
    recipient = models.CharField(max_length=200)
    content = models.TextField()
    sent_by = models.ForeignKey(User, on_delete=models.CASCADE)
    sent_at = models.DateTimeField(auto_now_add=True)
    job = models.ForeignKey(Job, on_delete=models.SET_NULL, null=True, blank=True)
    template = models.ForeignKey(EmailTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"Email to {self.recipient}: {self.subject}"