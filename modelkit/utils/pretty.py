from rich.markup import escape
from rich.tree import Tree


def pretty_print_type(typ):
    try:
        # For typing types
        s = typ._name
        if typ.__args__:
            s += "["
            s += ",".join(pretty_print_type(x) for x in typ.__args__)
            s += "]"
        return escape(s)
    except (AttributeError, TypeError):
        pass
    try:
        # For classes
        return escape(typ.__name__)
    except AttributeError:
        pass
    return escape(str(typ))


def describe(obj, t=None):
    if not t:
        t = Tree("")

    if hasattr(obj, "__fields__"):
        for field_name, field in obj.__fields__.items():
            sub_t = t.add(
                f"[deep_sky_blue1]{field_name}[/deep_sky_blue1] [dim]: "
                f"{pretty_print_type(field.outer_type_)}[/dim]"
            )
            describe(getattr(obj, field_name), t=sub_t)
    elif isinstance(obj, dict):
        if obj:
            for field_name, field in obj.items():
                sub_t = t.add(
                    f"[deep_sky_blue1]{escape(field_name)}[/deep_sky_blue1] [dim]: "
                    f"{pretty_print_type(type(field).__name__)}[/dim]"
                )
                describe(field, t=sub_t)
        else:
            t.label += " = [orange3]{}[/orange3]"
    elif isinstance(obj, type):
        t.label += f" = [orange3]{escape(str(obj.__name__))}[/orange3] type"
    elif isinstance(obj, (str, int, float, bool)):
        t.label += f" = [orange3]{escape(repr(obj))}[/orange3]"
    elif obj is None:
        t.label += " = [orange3]None[/orange3]"
    elif isinstance(obj, object):
        t.label += (
            f" = [orange3]{escape(str(obj.__class__.__name__))}[/orange3] " "instance"
        )
        try:
            obj.describe(t=t)
        except AttributeError:
            try:
                for var in vars(obj):
                    if var.startswith("_"):
                        continue
                    sub_t = t.add(
                        f"[deep_sky_blue1]{var}[/deep_sky_blue1] [dim]: "
                        f"{pretty_print_type(type(getattr(obj, var)).__name__)}"
                        f"[/dim] = {escape(repr(getattr(obj, var)))}"
                    )
            except TypeError:
                t.label += f" = [orange3]{escape(str(obj))}[/orange3]"
    return t
