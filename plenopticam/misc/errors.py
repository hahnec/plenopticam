class LfpTypeError(TypeError):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class LfpAttributeError(AttributeError):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class PlenopticamError(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)