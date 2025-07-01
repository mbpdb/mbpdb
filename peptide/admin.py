from django.contrib import admin
from .models import PeptideInfo, Submission, Counter, ProteinInfo, ProteinVariant, protein_pid, GitHubActions
from .toolbox import pepdb_approve, export_database, git_init, git_push
from django.urls import reverse
from django.utils.html import format_html
from django.urls import path
from django.template.response import TemplateResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator

class PeptideInfoAdmin(admin.ModelAdmin):
    list_display = ('peptide','time_approved')

    actions = ['export_selected_to_tsv']
    change_list_template = "admin/peptide/peptideinfo/change_list.html"

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('git-init/', self.admin_site.admin_view(self.git_init_view), name='git-init'),
            path('git-push/', self.admin_site.admin_view(self.git_push_view), name='git-push'),
        ]
        return custom_urls + urls

    def git_init_view(self, request):
        from .toolbox import git_init
        git_init(self, request, None)
        from django.shortcuts import redirect
        return redirect("..")

    def git_push_view(self, request):
        from .toolbox import git_push
        git_push(self, request, None)
        from django.shortcuts import redirect
        return redirect("..")

    def export_selected_to_tsv(self, request, queryset):
        # Generate TSV file
        from .toolbox import export_database
        response = export_database(request)
        # Modify the HttpResponse to indicate a TSV file download
        response['Content-Type'] = 'text/tsv'
        response['Content-Disposition'] = 'attachment; filename="exported_data.tsv"'
        return response

    export_selected_to_tsv.short_description = "Export selected to TSV"

admin.site.register(PeptideInfo, PeptideInfoAdmin)

class ProteinVariantAdmin(admin.ModelAdmin):
    list_display = (protein_pid,'pvid')
admin.site.register(ProteinVariant, ProteinVariantAdmin)

class ProteinInfoAdmin(admin.ModelAdmin):
    list_display = ('header', 'pid')

    # Add readonly_fields to include the new link field
    readonly_fields = ('add_protein_link',)

    # Define the function that returns the formatted HTML link
    def add_protein_link(self, obj=None):
        return format_html('<a href="{}">Add Proteins</a>', reverse('add_proteins'))

    # Add a short description for this field
    add_protein_link.short_description = 'Add Proteins'

admin.site.register(ProteinInfo, ProteinInfoAdmin)

class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('protein_id', 'peptide', 'function', 'additional_details', 'ic50' , 'inhibition_type','inhibited_microorganisms', 'title', 'authors', 'abstract', 'doi', 'intervals', 'length', 'time_submitted')

    def approve_submission(self, request, queryset):
        messages = pepdb_approve(queryset)
        for m in messages:
            self.message_user(request, m)
    approve_submission.short_description = "Approve selected submissions"

    actions = [approve_submission]

    #Added code to link to TSV_upload through the admin page. Added 8/21/23 RK
    readonly_fields = ('add_csv_link',)
    def add_csv_link(self, obj=None):
        return format_html('<a href="{}">MBPDB add multiple entries using TSV file</a>', reverse('peptide_db_csv'))

    add_csv_link.short_description = 'Upload TSV'
admin.site.register(Submission, SubmissionAdmin)

class CounterAdmin(admin.ModelAdmin):
    list_display = ('ip','access_time', 'page')

admin.site.register(Counter, CounterAdmin)

@staff_member_required
@csrf_protect
def github_git_init_view(request):
    if request.method == 'POST':
        from .toolbox import git_init
        git_init(None, request, None)
    from django.shortcuts import redirect
    return redirect('/admin/')

@staff_member_required
@csrf_protect
def github_git_push_view(request):
    if request.method == 'POST':
        from .toolbox import git_push
        git_push(None, request, None)
    from django.shortcuts import redirect
    return redirect('/admin/')

# Patch admin site to add custom URLs for GitHub actions

def get_custom_urls(original_get_urls):
    def custom_urls():
        urls = original_get_urls()
        custom = [
            path('github/git-init/', github_git_init_view, name='github-git-init'),
            path('github/git-push/', github_git_push_view, name='github-git-push'),
        ]
        return custom + urls
    return custom_urls

admin.site.get_urls = get_custom_urls(admin.site.get_urls)

class GitHubActionsAdmin(admin.ModelAdmin):
    change_list_template = "admin/peptide/github/change_list.html"
    def has_add_permission(self, request):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
    def has_change_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        # Return an empty queryset to avoid DB access
        return super().get_queryset(request).none()

    def changelist_view(self, request, extra_context=None):
        from django.shortcuts import redirect
        from django.contrib import messages
        if request.method == 'POST':
            if 'git_init' in request.POST:
                from .toolbox import git_init
                git_init(self, request, None)
                messages.success(request, "Git Init executed.")
            elif 'git_push' in request.POST:
                from .toolbox import git_push
                git_push(self, request, None)
                messages.success(request, "Git Push executed.")
            return redirect(request.path)
        return super().changelist_view(request, extra_context=extra_context)

admin.site.register(GitHubActions, GitHubActionsAdmin)