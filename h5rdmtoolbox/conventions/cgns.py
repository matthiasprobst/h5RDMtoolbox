"""Generates the standard name convention file for Fluids as proposed by CGNS
This is work in progress and as long as there is no official version provided by the community
this repository uses this convention
"""

from h5rdmtoolbox.conventions.standard_names import StandardNameConvention

cgns_standard_names_dict = {
    'Time': {'canonical_units': 's', 'description': 'physical time'},
    'VelocityX': {'canonical_units': 'm/s',
                   'description': 'velocity is a vector quantity. X indicates the component in x-axis direction'},
    'VelocityY': {'canonical_units': 'm/s',
                   'description': 'velocity is a vector quantity. Y indicates the component in y-axis direction'},
    'VelocityZ': {'canonical_units': 'm/s',
                   'description': 'velocity is a vector quantity. Z indicates the component in z-axis direction'},
    'VorticityZ': {'canonical_units': '1/s',
                    'description': 'vorticity is a vector quantity. Z indicates the component in z-axis direction'},
    'VelocityR' : {'canonical_units': 'm/s',
                    'description':	'vorticity is a vector quantity	. R indicates the component in radial direction'},
    'VelocityTheta' : {'canonical_units': 'm/s',
                    'description':	'vorticity is a vector quantity	. Theta indicates the component in theta-direction'},
    'VelocityPhi' : {'canonical_units': 'm/s',
                    'description':	'vorticity is a vector quantity	. Phi indicates the component in phi-direction'},
    'VelocityMagnitude': {'canonical_units': 'm/s',
                              'description': 'Magnitude of the vector quantity velocity.'},
    'CoordinateX': {'canonical_units': 'm', 'description': None},
    'CoordinateY': {'canonical_units': 'm', 'description': None},
    'CoordinateZ': {'canonical_units': 'm', 'description': None},
    'ReynoldsStressXX': {'canonical_units': 'm**2/s**2', 'description': None},
    'ReynoldsStressXY': {'canonical_units': 'm**2/s**2', 'description': None},
    'ReynoldsStressXZ': {'canonical_units': 'm**2/s**2', 'description': None},
    'ReynoldsStressYX': {'canonical_units': 'm**2/s**2', 'description': None},
    'ReynoldsStressYY': {'canonical_units': 'm**2/s**2', 'description': None},
    'ReynoldsStressYZ': {'canonical_units': 'm**2/s**2', 'description': None},
    'ReynoldsStressZX': {'canonical_units': 'm**2/s**2', 'description': None},
    'ReynoldsStressZY': {'canonical_units': 'm**2/s**2', 'description': None},
    'ReynoldsStressZZ': {'canonical_units': 'm**2/s**2', 'description': None},
    'Pressure': {'canonical_units': 'Pa', 'description': 'static pressure'},
    'TurbulentEnergyKinetic': {'canonical_units': 'm**2/s**2', 'description': None},
    'PressureDynamic': {'canonical_units': 'Pa', 'description': None},
    'PressureStagnation': {'canonical_units': 'Pa', 'description': None},
    'SoundPressure': {'canonical_units': 'Pa', 'description': None},
    'Temperature': {'canonical_units': 'K', 'description': None},
    'TemperatureStagnation': {'canonical_units': 'K', 'description': None}

}

piv_extended_cgns_standard_names_dict = cgns_standard_names_dict.copy()
piv_extended_cgns_standard_names_dict.update({
                                'PixelCoordinateX': {'canonical_units': 'pixel', 'description': None},
                                'PixelCoordinateY': {'canonical_units': 'pixel', 'description': None},
                                'Peak1DisplacementX': {'canonical_units': '', 'description': None},
                                'Peak2DisplacementX': {'canonical_units': '', 'description': None},
                                'Peak3DisplacementX': {'canonical_units': '', 'description': None},
                                'Peak1DisplacementY': {'canonical_units': '', 'description': None},
                                'Peak2DisplacementY': {'canonical_units': '', 'description': None},
                                'Peak3DisplacementY': {'canonical_units': '', 'description': None},
                                })



if __name__ == '__main__':
    """creating xml convention files in xml/folder which will be installed with the package.
    So if something is changed here, update the version (also repo versioN), write the xml file and re-install the 
    package"""
    import pathlib

    cgns_convention = StandardNameConvention(cgns_standard_names_dict, name='CGNS_Standard_Name',
                                              version=1, contact='matthias.probst@kit.edu',
                                              institution='Karlsruhe Institute of Technology')
    _ = cgns_convention.to_xml(pathlib.Path(__file__).parent / 'snxml' / f'cgns-v{cgns_convention.version}.xml')
    piv_convention = StandardNameConvention(piv_extended_standard_names_dict, name='PIV_extended_CGNS_Standard_Name',
                                            version=1, contact='matthias.probst@kit.edu',
                                            institution='Karlsruhe Institute of Technology')
    _ = piv_convention.to_xml(pathlib.Path(__file__).parent / 'snxml' / f'piv-v{piv_convention.version}.xml')