def user_role(request):
    if request.user.is_authenticated:
        is_manager = request.user.groups.filter(name="Менеджер").exists()
        return {"is_manager": is_manager}
    return {"is_manager": False}
