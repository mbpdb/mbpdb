from django import forms

class ListTextWidget(forms.TextInput):
    def __init__(self, data_list, name, *args, **kwargs):
        super(ListTextWidget, self).__init__(*args, **kwargs)
        self._name = name
        self._list = data_list
        self.attrs.update({'list':'list__%s' % self._name})

    def render(self, name, value, attrs=None):
        text_html = super(ListTextWidget, self).render(name, value, attrs=attrs)
        data_list = '<datalist id="list__%s">' % self._name
        for item in self._list:
            data_list += '<option value="%s">' % item
        data_list += '</datalist>'

        return (text_html + data_list)

class PeptideSearchForm(forms.Form):
    peptide = forms.CharField(label='Peptide Sequence', max_length=100)
    peptide_option = forms.ChoiceField(label='Sequence search options:', widget=forms.RadioSelect, choices=(('identical','Identical'),('contain','Contain'),('reverse','Reverse'),('similarity','Sequence similarity')))
    seqsim = forms.ChoiceField(choices = ((i,'%d%%' % i) for i in range(10,100,10)), label='')
    proteinid = forms.CharField(label='Protein ID', max_length=30)
    #function = forms.CharField(widget=ListTextWidget, data
