import re
from pydantic import (
    BaseModel,
)  

from validator_types import WrapValidator, Annotated


def _long_name(value, parent=None, attrs=None):
    pattern = re.compile(r"^[a-zA-Z].*(?<!\s)$")
    if not pattern.match(value):
        raise ValueError('Invalid format for pattern')
    return value


long_name = Annotated[str, WrapValidator(_long_name)]


class Long_nameValidator(BaseModel):
	long_name: long_name