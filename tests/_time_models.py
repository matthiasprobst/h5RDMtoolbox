"""

http://www.w3.org/2006/time#

"""
from datetime import date, datetime
from typing import Optional, Union

from pydantic import Field

from ontolutils import Thing, urirefs, namespaces
from ontolutils.typing import AnyIriOf


@namespaces(time="http://www.w3.org/2006/time#")
@urirefs(TRS='time:TRS',
         )
class TRS(Thing):
    """A temporal reference system, such as a temporal coordinate reference system (with an origin, direction,
    and scale), a calendar-clock combination, or a (possibly hierarchical) ordinal system."""
    pass


@namespaces(time="http://www.w3.org/2006/time#")
@urirefs(TemporalPosition='time:TemporalPosition',
         hasTRS='time:hasTRS',
         )
class TemporalPosition(Thing):
    """A temporal position described using either a (nominal) value from an ordinal reference system, or a (numeric)
    value in a temporal coordinate system. """
    hasTRS: Optional[AnyIriOf[TRS]] = Field(default=None, alias="has_trs")


@namespaces(time="http://www.w3.org/2006/time#")
@urirefs(TimePosition='time:TimePosition',
         nominalPosition='time:nominalPosition',
         numericPosition='time:numericPosition',
         )
class TimePosition(TemporalPosition):
    """A position on a temporal scale"""
    nominalPosition: Optional[str] = Field(default=None, alias="nominal_position")
    numericPosition: Optional[float] = Field(default=None, alias="numeric_position")


@namespaces(time="http://www.w3.org/2006/time#")
@urirefs(Instant='time:Instant',
         inXSDDate='time:inXSDDate',
         inXSDDateTime='time:inXSDDateTime',
         inXSDDateTimeStamp='time:inXSDDateTimeStamp',
         inside='time:inside',
         inTimePosition='time:inTimePosition',
         )
class Instant(Thing):
    inXSDDate: Optional[Union[str, date]] = Field(default=None, alias="date")
    inXSDDateTime: Optional[Union[str, datetime]] = Field(default=None, alias="datetime")
    inXSDDateTimeStamp: Optional[Union[str, datetime]] = Field(default=None, alias="time_stamp")
    inside: Optional["Interval"] = None
    inTimePosition: Optional[AnyIriOf[TimePosition]] = Field(
        default=None,
        alias="in_time_position"
    )




@namespaces(time="http://www.w3.org/2006/time#")
@urirefs(TemporalDuration='time:TemporalDuration')
class TemporalDuration(Instant):
    """Time extent; duration of a time interval separate from its particular start position"""

@namespaces(time="http://www.w3.org/2006/time#")
@urirefs(DurationDescription='time:DurationDescription')
class DurationDescription(Instant):
    """Description of temporal extent structured with separate values for the various elements of a calendar-clock
    system. The temporal reference system is fixed to Gregorian Calendar, and the range of each of the numeric
    properties is restricted to xsd:decimal"""

@namespaces(time="http://www.w3.org/2006/time#")
@urirefs(TemporalEntity='time:TemporalEntity',
         hasBeginning='time:hasBeginning',
         hasEnd='time:hasEnd',
         hasTemporalDuration='time:hasTemporalDuration',
         )
class TemporalEntity(Instant):
    hasBeginning: Optional[Instant] = Field(default=None, alias="has_beginning")
    hasEnd: Optional[Instant] = Field(default=None, alias="has_end")
    hasTemporalDuration: Optional[TemporalDuration] = Field(
        default=None,
        alias="has_temporal_duration"
    )
    hasDurationDescription: Optional[AnyIriOf[DurationDescription]] = Field(
        default=None,
        alias="has_temporal_duration"
    )


@namespaces(time="http://www.w3.org/2006/time#")
@urirefs(Interval='time:Interval')
class Interval(TemporalEntity):
    """A temporal entity with an extent or duration"""


Instant.model_rebuild()
