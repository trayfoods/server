from django.http import JsonResponse
from .models import School


def get_filtered_campus(request):
    selected_school_id = request.GET.get("selected_school", None)
    if selected_school_id is None:
        return JsonResponse({}, safe=False)
    # campuses looks like this: ["Campus 1", "Campus 2", "Campus 3"]
    data = School.objects.filter(id=selected_school_id).values_list(
        "campuses", flat=True
    )
    campuses = list(data)
    return JsonResponse(campuses[0], safe=False)
