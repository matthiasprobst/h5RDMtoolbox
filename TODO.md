# TODOs

## conventions

- attribute_convention --> attribute_convention: AttributeManager (special wrapper with special conventions) maybe for
  later version TODo AttributeManager should not take h5grp and h5ds but obj which passes self (could also be taken from
  self._id)
- sn_convention --> name_identifier: NameIdentifier --> controls "standard_name" & overwrites attribute_convention
- write NameIdentifier
- write CF(NameIdentifier)
- write CGNS(NameIdentifier)
- new attributes name --> "derived_from_[variable_name_path_in_file]" (velocity gradient), "measured"  (measured is also
  pressure [Pa] although it is originally voltage [v])
- new attributes beyond standard_names: measurement_location
  (like "area" in conventions: {'wall','before_[ something ]'}) (before_fan --> fan must be defined as well)
- valid_min, valid_max, valid_range, ancillary_ariables --> uncertainty or instment data --> point to datasets or groups
- use uncertainty as separate attribute which points to a dataset of same length or is a float. that dataset has the standard_name "standard_error" or "relative_error"
- use instrument attribute that points to a group or an dict-attribute or is an dict-attribute itself