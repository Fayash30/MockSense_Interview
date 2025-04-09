from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from .forms import RegisterForm
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

def user_login(request):
    if request.user.is_authenticated:
        return redirect('quiz_view')

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        
        try:
            user_exists = User.objects.get(username=username)
        except User.DoesNotExist:
            messages.error(request, 'User does not exist.')
            return render(request, 'accounts/login.html')

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('quiz_view')
        else:
            messages.error(request, 'Incorrect password.')
            
    return render(request, 'accounts/login.html')

def register(request):
    if request.user.is_authenticated:
        return redirect('quiz_view')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            messages.success(request, 'Account created successfully!')
            return redirect('login')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})

@csrf_exempt
def user_logout(request):
    if request.method == 'POST':
        logout(request)
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse({'success': True})
    return redirect('login')

def home(request):
    return render(request, "accounts/index.html")