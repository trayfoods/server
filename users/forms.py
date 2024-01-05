from django import forms
from django.core.exceptions import ValidationError
from .models import School, Hostel

class HostelForm(forms.ModelForm):

    class Meta:
        model = Hostel
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        campus = cleaned_data.get('campus')
        school = cleaned_data.get('school')

        if campus and school:
            school = School.objects.get(id=school.id)
            campuses = school.campuses
            if not campus in campuses:
                raise ValidationError("The selected campus is not related to the selected school. The selected school has the following campuses: " + str(campuses))

        return cleaned_data