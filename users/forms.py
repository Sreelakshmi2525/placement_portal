from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, StudentProfile

class StudentRegistrationForm(UserCreationForm):
    roll_number = forms.CharField(max_length=20)
    department = forms.CharField(max_length=100)
    year_of_study = forms.IntegerField(min_value=1, max_value=5)
    image = forms.ImageField(required=False)  # Optional profile image field

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 'student'

        if commit:
            user.save()
            StudentProfile.objects.create(
                user=user,
                roll_number=self.cleaned_data.get('roll_number'),
                department=self.cleaned_data.get('department'),
                year_of_study=self.cleaned_data.get('year_of_study'),
                image=self.cleaned_data.get('image')  # Save uploaded image
            )
        return user
    
from django import forms
from .models import StudentProfile

class ProfileImageUpdateForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ["image"]

