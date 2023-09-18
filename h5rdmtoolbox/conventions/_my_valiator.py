import re
from pydantic import (
    BaseModel,
)
from pydantic.functional_validators import WrapValidator
from typing_extensions import Annotated


def _regex_validator(value, parent=None, attrs=None):
    pattern = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}(\d|X)$")
    if not pattern.match(value):
        raise ValueError('Invalid format for pattern')
    return value


regex = Annotated[int, WrapValidator(_regex_validator)]


class ContactValidator(BaseModel):
    name: str
    orcid: regex


ContactValidator(name='awd', orcid='0000-0002-1825-0097')
