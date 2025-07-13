class Label:
    def __init__(self, **kwargs):
        self.text = kwargs.get('text', '')

    def setter(self, attr):
        def _set(value):
            setattr(self, attr, value)
        return _set
