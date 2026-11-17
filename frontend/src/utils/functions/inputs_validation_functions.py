def dropdown_check_for_blank_selected(selected: list[any], default):
    if len(selected) == 0:
        return default
    else:
        return selected
