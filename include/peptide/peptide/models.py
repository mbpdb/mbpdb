from django.db import models

# Create your models here.

def protein_pid(obj):
    return ("%s" % obj.protein.pid)

class ProteinInfo(models.Model):
    header = models.CharField(max_length=1000)
    pid = models.CharField(max_length=30)
    seq = models.CharField(max_length=5000)
    desc = models.CharField(max_length=500)
    species = models.CharField(max_length=70)

class ProteinVariant(models.Model):
    seq = models.CharField(max_length=5000)
    pvid = models.CharField(max_length=30)
    protein = models.ForeignKey(ProteinInfo, on_delete=models.CASCADE, related_name="orig_proteins")

class PeptideInfo(models.Model):
    peptide = models.CharField(max_length=300)
    protein = models.ForeignKey(ProteinInfo, on_delete=models.CASCADE, related_name="proteins")
    protein_variants = models.CharField(max_length=100,default='')
    intervals = models.CharField(max_length=100)
    length = models.IntegerField()
    category = models.CharField(max_length=50)
    time_approved = models.DateTimeField()
    def __unicode__(self):
        return(self.peptide)

class Function(models.Model):
    pep = models.ForeignKey(PeptideInfo, related_name="functions", on_delete=models.CASCADE)
    function = models.CharField(max_length=400)

class Reference(models.Model):
    func = models.ForeignKey(Function, related_name="references", on_delete=models.CASCADE)
    title = models.CharField(max_length=300)
    authors = models.CharField(max_length=300)
    abstract = models.CharField(max_length=1000)
    doi = models.CharField(max_length=100)
    secondary_func = models.CharField(max_length=400, default='')
    ptm = models.CharField(max_length=200, default='')

class Submission(models.Model):
    #proteinID, peptide, category, function, secondary_function, title, authors, abstract, and doi
    protein_id = models.CharField(max_length=30)
    protein_variants = models.CharField(max_length=30,default='')
    peptide = models.CharField(max_length=300)
    category = models.CharField(max_length=50)
    function = models.CharField(max_length=400)
    secondary_function = models.CharField(max_length=400, default='')
    ptm = models.CharField(max_length=200, default='')
    title = models.CharField(max_length=300)
    authors = models.CharField(max_length=300)
    abstract = models.CharField(max_length=1000)
    doi = models.CharField(max_length=100)
    intervals = models.CharField(max_length=100)
    length = models.IntegerField()
    time_submitted = models.DateTimeField()


class Counter(models.Model):
    ip = models.CharField(max_length=40)
    access_time = models.DateTimeField()
    page = models.CharField(max_length=40)

"""
peptides = PeptideInfo.objects.filter(sequence__icontains="ABAB",length__gte=4)
for peptide in peptides:
    print peptide.sequence
    for reference in peptide.references.all():
        print reference.author
"""
