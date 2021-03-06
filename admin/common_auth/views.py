from __future__ import absolute_import, unicode_literals

from django.core.urlresolvers import reverse, reverse_lazy
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.generic.edit import FormView, UpdateView, CreateView
from django.contrib import messages
from django.contrib.auth.models import Group
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth import login, REDIRECT_FIELD_NAME, authenticate, logout

from website.settings import PREREG_ADMIN_TAG

from osf.models.user import OSFUser
from admin.common_auth.models import AdminProfile
from admin.common_auth.forms import LoginForm, UserRegistrationForm, DeskUserForm


class LoginView(FormView):
    form_class = LoginForm
    redirect_field_name = REDIRECT_FIELD_NAME
    template_name = 'login.html'

    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        return super(LoginView, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = authenticate(
            username=form.cleaned_data.get('email').strip(),
            password=form.cleaned_data.get('password').strip()
        )
        if user is not None:
            login(self.request, user)
        else:
            messages.error(
                self.request,
                'Email and/or Password incorrect. Please try again.'
            )
            return redirect('auth:login')
        return super(LoginView, self).form_valid(form)

    def get_success_url(self):
        redirect_to = self.request.GET.get(self.redirect_field_name, '')
        if not redirect_to or redirect_to == '/':
            redirect_to = reverse('home')
        return redirect_to


def logout_user(request):
    logout(request)
    return redirect('auth:login')


class RegisterUser(PermissionRequiredMixin, FormView):
    form_class = UserRegistrationForm
    template_name = 'register.html'
    permission_required = 'osf.change_user'
    raise_exception = True

    def form_valid(self, form):
        osf_id = form.cleaned_data.get('osf_id')
        osf_user = OSFUser.load(osf_id)

        if not osf_user:
            raise Http404('OSF user with id "{}" not found. Please double check.'.format(osf_id))

        osf_user.is_staff = True
        osf_user.save()

        # create AdminProfile for this new user
        profile, created = AdminProfile.objects.get_or_create(user=osf_user)
        if not created:
            return HttpResponseBadRequest(
                'This user is already able to access the OSF Admin - please update their permissions with a superuser'
            )

        prereg_admin_group = Group.objects.get(name='prereg_admin')
        for group in form.cleaned_data.get('group_perms'):
            osf_user.groups.add(group)
            if group == prereg_admin_group:
                osf_user.add_system_tag(PREREG_ADMIN_TAG)

        osf_user.save()

        messages.success(self.request, 'Registration successful for OSF User {}!'.format(osf_user.username))
        return super(RegisterUser, self).form_valid(form)

    def get_success_url(self):
        return reverse('auth:register')


class DeskUserCreateFormView(PermissionRequiredMixin, CreateView):
    form_class = DeskUserForm
    template_name = 'desk/settings.html'
    success_url = reverse_lazy('auth:desk')
    permissions_required = 'admin.view_desk'
    raise_exception = True

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super(DeskUserCreateFormView, self).form_valid(form)


class DeskUserUpdateFormView(PermissionRequiredMixin, UpdateView):
    form_class = DeskUserForm
    template_name = 'desk/settings.html'
    success_url = reverse_lazy('auth:desk')
    permissions_required = 'admin.view_desk'
    raise_exception = True

    def get_object(self, queryset=None):
        return self.request.user.admin_profile
