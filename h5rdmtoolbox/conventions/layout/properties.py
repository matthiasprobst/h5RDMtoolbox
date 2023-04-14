import h5py


class PropertyValidator:

    def __init__(self, property_name: str, validator: "Validator"):
        self.property_name = property_name
        self.validator = validator

    def __repr__(self):
        return f'<PropertyValidator({self.validator.__repr__()})>'

    def __call__(self, target: h5py.Dataset):
        property_value = target.__getattribute__(self.property_name)
        if self.property_name == 'name':
            property_value = property_value.strip('/')
        return self.validator(property_value)  # call the validator


class PropertyValidatorWrapper:
    """Wrapper around a basic Validator like `Equal` for example. It enables
    to compare the value of a property of a dataset to a reference value."""

    def __call__(self, property_name: str, validator: "Validator") -> PropertyValidator:
        return PropertyValidator(property_name, validator)
