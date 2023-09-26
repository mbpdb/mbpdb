from django.db import models

# Create your models here.

def protein_pid(obj):
    return ("%s" % obj.protein.pid)

class ProteinInfo(models.Model):
    header = models.CharField(max_length=1000)
    pid = models.CharField(max_length=30)
    seq = models.CharField(max_length=10000)
    desc = models.CharField(max_length=500)
    species = models.CharField(max_length=150)

class ProteinVariant(models.Model):
    seq = models.CharField(max_length=10000)
    pvid = models.CharField(max_length=30)
    protein = models.ForeignKey(ProteinInfo, on_delete=models.CASCADE, related_name="orig_proteins")

class PeptideInfo(models.Model):
    peptide = models.CharField(max_length=500)
    protein = models.ForeignKey(ProteinInfo, on_delete=models.CASCADE, related_name="proteins")
    protein_variants = models.CharField(max_length=100,default='')
    intervals = models.CharField(max_length=100)
    length = models.IntegerField()
    time_approved = models.DateTimeField()
    def __unicode__(self):
        return(self.peptide)

class Function(models.Model):
    pep = models.ForeignKey(PeptideInfo, related_name="functions", on_delete=models.CASCADE)
    function = models.CharField(max_length=400)
    class Meta:
        unique_together = [['pep', 'function']]
class Reference(models.Model):
    func = models.ForeignKey(Function, related_name="references", on_delete=models.CASCADE)
    title = models.CharField(max_length=300)
    authors = models.CharField(max_length=300)
    abstract = models.CharField(max_length=1000)
    doi = models.CharField(max_length=100)
    additional_details = models.CharField(max_length=400, default='')
    ptm = models.CharField(max_length=200, default='')
    ic50 = models.FloatField(null=True, blank=True)
    inhibition_type = models.TextField(null=True, blank=True)
    inhibited_microorganisms = models.TextField(null=True, blank=True)

class Submission(models.Model):
    #proteinID, peptide, function, secondary_function, title, authors, abstract, and doi
    protein_id = models.CharField(max_length=30)
    protein_variants = models.CharField(max_length=30,default='')
    peptide = models.CharField(max_length=300)
    function = models.CharField(max_length=400)
    additional_details = models.CharField(max_length=400, default='')
    ptm = models.CharField(max_length=200, default='')
    title = models.CharField(max_length=300)
    authors = models.CharField(max_length=300)
    abstract = models.CharField(max_length=1000)
    doi = models.CharField(max_length=100)
    intervals = models.CharField(max_length=100)
    length = models.IntegerField()
    time_submitted = models.DateTimeField()
    ic50 = models.FloatField(null=True, blank=True)
    inhibition_type = models.TextField(null=True, blank=True)
    inhibited_microorganisms = models.TextField(null=True, blank=True)

class Counter(models.Model):
    ip = models.CharField(max_length=40)
    access_time = models.DateTimeField()
    page = models.CharField(max_length=40)