from django import forms
from .models import User, Event, Bib, EventManager, CloudStorage

class UserUpdateForm(forms.ModelForm):
    created_timestamp = forms.DateTimeField(
        required=False,
        disabled=True,
        label='Created',
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
    )

    updated_timestamp = forms.DateTimeField(
        required=False,
        disabled=True,
        label='Last Updated',
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
    )

    class Meta:
        model = User
        fields = ['email', 'name', 'phone', 'api_key', 'description']
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
            }),
        }

    def __init__(self, *args, **kwargs):
        for_admin = kwargs.pop('for_admin', False)  # new flag
        super().__init__(*args, **kwargs)

        self.fields['created_timestamp'].initial = self.instance.created_timestamp
        self.fields['updated_timestamp'].initial = self.instance.updated_timestamp

        # If for admin, add the 'enabled' and 'role' fields
        if for_admin:
            self.fields['enabled'] = forms.BooleanField(
                required=False,
                label='Enabled',
                initial=self.instance.enabled if self.instance.id else True,
                widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
            )

            self.fields['role'] = forms.ChoiceField(
                choices=[('admin', 'Admin'), ('user', 'User')],  # Assuming 'admin' and 'user' roles
                label='Role',
                initial=self.instance.role if self.instance.id else 'user',
                widget=forms.Select(attrs={'class': 'form-control'})
            )

            # Insert 'enabled' and 'role' after 'name'
            field_order = []
            for field in self.fields:
                field_order.append(field)
                if field == 'name':  # Place 'enabled' and 'role' after 'name'
                    field_order.append('role')
                    field_order.append('enabled')
            self.order_fields(field_order)

    def clean_created_timestamp(self):
        return self.instance.created_timestamp

    def clean_updated_timestamp(self):
        return self.instance.updated_timestamp

    def save(self, commit=True):
        instance = super().save(commit=False)
        if 'enabled' in self.cleaned_data:
            instance.enabled = self.cleaned_data['enabled']
        if 'role' in self.cleaned_data:
            instance.role = self.cleaned_data['role']
        if commit:
            instance.save()
        return instance

class EventForm(forms.ModelForm):
    manager = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        label="Event Manager",
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = Event
        fields = ['name', 'enabled', 'expiry']
        widgets = {
            'expiry': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        current_manager_id = kwargs.pop('current_manager_id', None)
        super().__init__(*args, **kwargs)
        if current_manager_id:
            self.fields['manager'].initial = current_manager_id
        self.fields['manager'].label_from_instance = lambda obj: f"{obj.name} ({obj.email})"

class BibForm(forms.ModelForm):
    event = forms.ModelChoiceField(
        queryset=Event.objects.none(),  # will be set in __init__
        label='Event',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Bib
        fields = ['event', 'bib_number', 'name', 'code', 'enabled', 'expiry']
        widgets = {
            'expiry': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super().__init__(*args, **kwargs)

        if user.is_superuser:
            self.fields['event'].queryset = Event.objects.all().order_by('name')
        else:
            self.fields['event'].queryset = Event.objects.filter(
                id__in=EventManager.objects.filter(user_id=user.id).values_list('event_id', flat=True)
            ).order_by('name')

class CloudStorageForm(forms.ModelForm):
    class Meta:
        model = CloudStorage
        fields = ['event', 'url', 'recursive', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        if user.is_superuser:
            self.fields['event'].queryset = Event.objects.all().order_by('name')
        else:
            self.fields['event'].queryset = Event.objects.filter(
                id__in=EventManager.objects.filter(user_id=user.id).values('event_id', flat=True)
            ).order_by('name')