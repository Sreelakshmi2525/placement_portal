from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from .forms import StudentRegistrationForm
from .models import User, StudentProfile
from .forms import ProfileImageUpdateForm
from django.contrib import messages


def register_student(request):
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST, request.FILES)  # Include files for image upload
        if form.is_valid():
            user = form.save(commit=False)
            user.save()
            
            # Save StudentProfile with the image
            student_profile = StudentProfile.objects.create(
                user=user,
                roll_number=form.cleaned_data.get('roll_number'),
                department=form.cleaned_data.get('department'),
                year_of_study=form.cleaned_data.get('year_of_study'),
                image=form.cleaned_data.get('image')  # Save uploaded image
            )
            student_profile.save()

            # Authenticate and log in the user
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            login(request, user)
            return redirect('dashboard')
    else:
        form = StudentRegistrationForm()
    
    return render(request, 'users/register.html', {'form': form})

@login_required(login_url='login')
def dashboard(request):
    if request.user.is_authenticated:
        if request.user.is_student():
            student_profile = request.user.student_profile  # Get student profile details
            return render(request, 'users/student_dashboard.html', {'student_profile': student_profile})
        elif request.user.is_placement_officer():
            return render(request, 'users/plo_dashboard.html')

    return redirect('login')

def custom_logout(request):
    logout(request)
    request.session.flush()
    return redirect('login')

@login_required
def profile_view(request):
    profile = request.user.student_profile  # Get the user's profile

    if request.method == "POST":
        form = ProfileImageUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile picture updated successfully!")
            return redirect("profile")  # Redirect to refresh the page
    else:
        form = ProfileImageUpdateForm(instance=profile)

    return render(request, "users/profile.html", {"profile": profile, "form": form})

@login_required
def student_profiles(request):
    if request.user.is_placement_officer():  
        students = StudentProfile.objects.all()
        return render(request, "users/student_profiles.html", {"students": students})
    else:
        return render(request, "users/unauthorized.html")  # Redirect unauthorized users