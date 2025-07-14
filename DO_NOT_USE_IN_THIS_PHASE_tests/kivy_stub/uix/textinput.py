class TextInput:
    def __init__(self, **kwargs):
        self.text = kwargs.get('text', '')
        self.multiline = kwargs.get('multiline', False)
