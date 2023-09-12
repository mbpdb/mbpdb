from django.contrib import admin
from .models import PeptideInfo, Submission, Counter, ProteinInfo, ProteinVariant, protein_pid
from .toolbox import pepdb_approve, export_database
from django.urls import reverse
from django.utils.html import format_html

class PeptideInfoAdmin(admin.ModelAdmin):
    list_display = ('peptide','time_approved')

    actions = ['export_selected_to_tsv']

    def export_selected_to_tsv(self, request, queryset):
        # Generate TSV file
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
    list_display = ('protein_id', 'peptide', 'function', 'secondary_function', 'title', 'authors', 'abstract', 'doi', 'intervals', 'length', 'time_submitted')

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