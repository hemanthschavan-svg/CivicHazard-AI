DEPARTMENT_IDS = {
    "Roads": 1,
    "Electrical": 2,
    "Drainage": 3,
    "Sanitation": 4,
}

DEPARTMENT_NAMES = {
    department_id: name
    for name, department_id in DEPARTMENT_IDS.items()
}
