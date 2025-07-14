class StringProperty:
    def __init__(self, default=""):
        self.default = default
        self.name = None

    def __set_name__(self, owner, name):
        self.name = f"_{name}"

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return getattr(instance, self.name, self.default)

    def __set__(self, instance, value):
        setattr(instance, self.name, value)

class BooleanProperty:
    def __init__(self, default=False):
        self.default = default
        self.name = None

    def __set_name__(self, owner, name):
        self.name = f"_{name}"

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return getattr(instance, self.name, self.default)

    def __set__(self, instance, value):
        setattr(instance, self.name, value)

class NumericProperty:
    def __init__(self, default=0):
        self.default = default
        self.name = None

    def __set_name__(self, owner, name):
        self.name = f"_{name}"

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return getattr(instance, self.name, self.default)

    def __set__(self, instance, value):
        setattr(instance, self.name, value)
