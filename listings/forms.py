from django import forms

from .models import AvailabilityBlock, Property


class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = [
            "title", "description", "type", "status",
            "region", "city", "address", "latitude", "longitude",
            "rooms", "beds", "max_guests", "area_sqm",
            "base_price", "weekend_price", "cleaning_fee",
            "min_nights", "instant_booking", "cancellation_policy", "amenities",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "amenities": forms.CheckboxSelectMultiple,
        }


class BlockForm(forms.ModelForm):
    class Meta:
        model = AvailabilityBlock
        fields = ["start_date", "end_date", "reason"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }
