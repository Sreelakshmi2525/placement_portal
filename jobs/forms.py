# jobs/forms.py
from django import forms
from .models import Job, Department, EmailTemplate

class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = ['title', 'company', 'description', 'requirements', 'location', 'salary', 'url', 'status', 'departments']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'requirements': forms.Textarea(attrs={'rows': 5}),
        }

class JobScrapeForm(forms.Form):
    keyword = forms.CharField(max_length=100, help_text="Job title or keyword")
    location = forms.CharField(max_length=100, help_text="City, state, or remote")
    limit = forms.IntegerField(min_value=1, max_value=50, initial=10, help_text="Number of results to fetch")

# jobs/forms.py
# Add these forms
class EmailTemplateForm(forms.ModelForm):
    class Meta:
        model = EmailTemplate
        fields = ['name', 'subject', 'content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 10}),
        }

class EmailForm(forms.Form):
    recipient = forms.EmailField(required=True)
    cc = forms.EmailField(required=False)
    subject = forms.CharField(max_length=200, required=True)
    content = forms.CharField(widget=forms.Textarea(attrs={'rows': 10}), required=True)
    template = forms.ModelChoiceField(queryset=EmailTemplate.objects.none(), required=False)
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(EmailForm, self).__init__(*args, **kwargs)
        if user:
            self.fields['template'].queryset = EmailTemplate.objects.filter(created_by=user)