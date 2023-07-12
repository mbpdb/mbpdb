from django.contrib import admin
from .models import PeptideInfo, Submission, Counter, ProteinInfo, ProteinVariant, protein_pid
from .toolbox import pepdb_approve

class PeptideInfoAdmin(admin.ModelAdmin):
    list_display = ('peptide','category')
admin.site.register(PeptideInfo, PeptideInfoAdmin)

class ProteinVariantAdmin(admin.ModelAdmin):
    list_display = (protein_pid,'pvid')
admin.site.register(ProteinVariant, ProteinVariantAdmin)

class ProteinInfoAdmin(admin.ModelAdmin):
    list_display = ('header','pid')
admin.site.register(ProteinInfo, ProteinInfoAdmin)

class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('protein_id', 'peptide', 'category', 'function', 'secondary_function', 'title', 'authors', 'abstract', 'doi', 'intervals', 'length', 'time_submitted')

    def approve_submission(self, request, queryset):
        messages = pepdb_approve(queryset)
        for m in messages:
            self.message_user(request, m)
    approve_submission.short_description = "Approve selected submissions"

    actions = [approve_submission]

admin.site.register(Submission, SubmissionAdmin)

class CounterAdmin(admin.ModelAdmin):
    list_display = ('ip','access_time', 'page')
admin.site.register(Counter, CounterAdmin)
