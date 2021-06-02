def construct_recursive(cls, _fields_set=None, **values):
    # https://github.com/samuelcolvin/pydantic/issues/1168
    m = cls.__new__(cls)
    fields_values = {}

    for name, field in cls.__fields__.items():
        key = field.alias
        if key in values:  # this check is necessary or Optional fields will crash
            try:
                # if issubclass(field.type_, BaseModel):  # this is cleaner but slower
                if field.shape == 2:
                    fields_values[name] = [
                        construct_recursive(field.type_, **e) for e in values[key]
                    ]
                else:
                    fields_values[name] = construct_recursive(
                        field.outer_type_, **values[key]
                    )
            except (AttributeError, TypeError):
                if values[key] is None and not field.required:
                    fields_values[name] = field.get_default()
                else:
                    fields_values[name] = values[key]
        elif not field.required:
            fields_values[name] = field.get_default()

    object.__setattr__(m, "__dict__", fields_values)
    if _fields_set is None:
        _fields_set = set(values.keys())
    object.__setattr__(m, "__fields_set__", _fields_set)
    m._init_private_attributes()
    return m
