class ProgressBar:
    def __init__(self, **kwargs):
        self.value = kwargs.get('value', 0)

    def setter(self, attr):
        def _set(value):
            setattr(self, attr, value)
        return _set
