"""
Unit tests for check_variables() function using pytest.

Tests are organized by validation requirement:
1. Variable presence (Mandatory vs Optional)
2. Scalar requirement
3. Data type validation
4. Value range validation
5. Attribute presence and validation
"""

import pytest
import numpy as np
from netCDF4 import Dataset
import tempfile
import os
from fm301_cc import check_variables


class NetCDFTestDataFactory:
    """Factory for creating test netCDF datasets."""
    
    @staticmethod
    def create_test_dataset(variables_spec):
        """
        Create a temporary netCDF dataset with specified variables.
        
        Args:
            variables_spec: dict mapping variable names to specs
                {
                    'var_name': {
                        'shape': (),  # () for scalar, (size,) for array
                        'dtype': np.float32,
                        'value': 3.14,
                        'attributes': {'attr1': value1}
                    }
                }
        
        Returns:
            tuple: (dataset, tmp_path)
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix='.nc') as tmp:
            tmp_path = tmp.name
        
        ds = Dataset(tmp_path, 'w', format='NETCDF4')
        
        for var_name, spec in variables_spec.items():
            shape = spec.get('shape', ())
            dtype = spec.get('dtype', np.float32)
            value = spec.get('value', 0)
            attributes = spec.get('attributes', {})
            
            # Create dimension if needed
            if shape != ():
                dim_name = f'dim_{var_name}'
                ds.createDimension(dim_name, shape[0])
                var = ds.createVariable(var_name, dtype, (dim_name,))
                if isinstance(value, (list, np.ndarray)):
                    var[:] = value
                else:
                    var[:] = [value] * shape[0]
            else:
                # Scalar variable
                var = ds.createVariable(var_name, dtype)
                if dtype is str or np.dtype(dtype) == np.dtype('O'):
                    var[...] = value
                else:
                    var.assignValue(value)
            
            # Add attributes
            for attr_name, attr_value in attributes.items():
                setattr(var, attr_name, attr_value)
        
        # Close and reopen in read mode to ensure consistency
        ds.close()
        ds = Dataset(tmp_path, 'r')
        
        return ds, tmp_path
    
    @staticmethod
    def cleanup(ds, tmp_path):
        """Close dataset and remove temporary file."""
        ds.close()
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@pytest.fixture
def test_results():
    """Fixture providing results and section_summaries containers."""
    return {"results": [], "section_summaries": {}}


@pytest.fixture
def cleanup_fixture():
    """
    Fixture for cleanup after tests.
    This generator is driven by pytest itself, and will yield a function to register datasets for cleanup.
    It is initially called before the test function runs when the fixture is requested.
    After the test function completes, the yield will resume and it will clean up all registered datasets.
    """
    datasets_to_cleanup = []
    
    def register(ds, tmp_path):
        datasets_to_cleanup.append((ds, tmp_path))
    
    yield register
    
    for ds, tmp_path in datasets_to_cleanup:
        NetCDFTestDataFactory.cleanup(ds, tmp_path)


# ============================================================================
# Test: Variable Presence Requirements
# ============================================================================

class TestCheckVariablesPresence:
    """Test variable presence requirements: Mandatory vs Optional."""
    
    def test_mandatory_variable_present_passes(self, test_results, cleanup_fixture):
        """Mandatory variable that is present should PASS."""
        ds, tmp_path = NetCDFTestDataFactory.create_test_dataset({
            'mandatory_available_var': {
                'shape': (),
                'dtype': np.float32,
                'value': 65.5
            }
        })
        
        # register the dataset for cleanup after the test
        cleanup_fixture(ds, tmp_path)
        
        metadata = {
            'Global_Ancillary_variables': [
                {
                    'name': 'mandatory_available_var',
                    'type': 'float',
                    'applicability': 'Mandatory',
                    'attributes': []
                }
            ]
        }
        
        check_variables(ds, metadata, 'Global_Ancillary_variables', 
                      test_results['results'], test_results['section_summaries'])
        
        assert test_results['results'][0][-1] == 'pass'
        assert test_results['section_summaries']['Global_Ancillary_variables'][0] == 1
    
    def test_mandatory_variable_missing_fails(self, test_results, cleanup_fixture):
        """Mandatory variable that is missing should FAIL_MANDATORY."""
        ds, tmp_path = NetCDFTestDataFactory.create_test_dataset({})
        cleanup_fixture(ds, tmp_path)
        
        metadata = {
            'Global_Ancillary_variables': [
                {
                    'name': 'missing_mandatory_var',
                    'type': 'float',
                    'applicability': 'Mandatory',
                    'attributes': []
                }
            ]
        }
        
        check_variables(ds, metadata, 'Global_Ancillary_variables',
                      test_results['results'], test_results['section_summaries'])
        
        assert test_results['results'][0][-1] == 'fail_mandatory'
        assert test_results['section_summaries']['Global_Ancillary_variables'][1] == 1
    
    def test_optional_variable_missing_marked_not_used(self, test_results, cleanup_fixture):
        """Optional variable that is missing should be marked as NOT_USED."""
        ds, tmp_path = NetCDFTestDataFactory.create_test_dataset({})
        cleanup_fixture(ds, tmp_path)
        
        metadata = {
            'Global_Ancillary_variables': [
                {
                    'name': 'optional_missing_var',
                    'type': 'float',
                    'applicability': 'Optional',
                    'attributes': []
                }
            ]
        }
        
        check_variables(ds, metadata, 'Global_Ancillary_variables',
                      test_results['results'], test_results['section_summaries'])
        
        assert test_results['results'][0][-1] == 'not_used'
    
    def test_optional_variable_present_passes(self, test_results, cleanup_fixture):
        """Optional variable that is present should PASS (if type matches)."""
        ds, tmp_path = NetCDFTestDataFactory.create_test_dataset({
            'optional_present_var': {
                'shape': (),
                'dtype': np.float32,
                'value': 65.5
            }
        })
        cleanup_fixture(ds, tmp_path)
        
        metadata = {
            'Global_Ancillary_variables': [
                {
                    'name': 'optional_present_var',
                    'type': 'float',
                    'applicability': 'Optional',
                    'attributes': []
                }
            ]
        }
        
        check_variables(ds, metadata, 'Global_Ancillary_variables',
                      test_results['results'], test_results['section_summaries'])
        
        assert test_results['results'][0][-1] == 'pass'


# ============================================================================
# Test: Scalar Requirement
# ============================================================================

class TestCheckVariablesScalarRequirement:
    """Test scalar requirement: Global Ancillary variables must be scalar."""
    
    def test_scalar_variable_passes_scalar_check(self, test_results, cleanup_fixture):
        """A scalar variable should pass the scalar requirement."""
        ds, tmp_path = NetCDFTestDataFactory.create_test_dataset({
            'scalar_var': {
                'shape': (),
                'dtype': np.float32,
                'value': 25.5
            }
        })
        cleanup_fixture(ds, tmp_path)
        
        metadata = {
            'Global_Ancillary_variables': [
                {
                    'name': 'scalar_var',
                    'type': 'float',
                    'applicability': 'Mandatory',
                    'attributes': []
                }
            ]
        }
        
        check_variables(ds, metadata, 'Global_Ancillary_variables',
                      test_results['results'], test_results['section_summaries'])
        
        assert test_results['results'][0][-1] == 'pass'

    def test_1d_char_array_represents_string_passes_scalar_check(self, test_results, cleanup_fixture):
        """A 1D S1 char array representing a string should pass as scalar string."""
        ds, tmp_path = NetCDFTestDataFactory.create_test_dataset({
            '1d_char_array_var': {
                'shape': (5,),
                'dtype': np.dtype('S1'),
                'value': np.array(list('MIRA5'), dtype='S1')
            }
        })
        cleanup_fixture(ds, tmp_path)

        metadata = {
            'Global_Ancillary_variables': [
                {
                    'name': '1d_char_array_var',
                    'type': 'string',
                    'applicability': 'Mandatory',
                    'attributes': []
                }
            ],
            'allowed_values': {
                '1d_char_array_var': ['MIRA5']
            }
        }

        check_variables(ds, metadata, 'Global_Ancillary_variables',
                      test_results['results'], test_results['section_summaries'])

        assert test_results['results'][0][6] == 'MIRA5'
        assert test_results['results'][0][-1] == 'pass'
    
    def test_1d_array_fails_scalar_check(self, test_results, cleanup_fixture):
        """A 1D array should FAIL the scalar requirement."""
        ds, tmp_path = NetCDFTestDataFactory.create_test_dataset({
            'no_scalar_var': {
                'shape': (5,),
                'dtype': np.float32,
                'value': [25.5, 26.0, 25.8, 26.2, 25.9]
            }
        })
        cleanup_fixture(ds, tmp_path)
        
        metadata = {
            'Global_Ancillary_variables': [
                {
                    'name': 'no_scalar_var',
                    'type': 'float',
                    'applicability': 'Mandatory',
                    'attributes': []
                }
            ]
        }
        
        check_variables(ds, metadata, 'Global_Ancillary_variables',
                      test_results['results'], test_results['section_summaries'])
        
        assert test_results['results'][0][-1] == 'fail_mandatory'


# ============================================================================
# Test: Data Type Validation
# ============================================================================

class TestCheckVariablesDataType:
    """Test data type validation."""
    
    def test_correct_float_type_passes(self, test_results, cleanup_fixture):
        """Variable with correct float type should pass."""
        ds, tmp_path = NetCDFTestDataFactory.create_test_dataset({
            'a_float_var': {
                'shape': (),
                'dtype': np.float32,
                'value': 25.5
            }
        })
        cleanup_fixture(ds, tmp_path)
        
        metadata = {
            'Global_Ancillary_variables': [
                {
                    'name': 'a_float_var',
                    'type': 'float',
                    'applicability': 'Mandatory',
                    'attributes': []
                }
            ]
        }
        
        check_variables(ds, metadata, 'Global_Ancillary_variables',
                      test_results['results'], test_results['section_summaries'])
        
        assert test_results['results'][0][-1] == 'pass'
    
    def test_double_type_passes(self, test_results, cleanup_fixture):
        """Variable with double (float64) type should pass."""
        ds, tmp_path = NetCDFTestDataFactory.create_test_dataset({
            'a_double_var': {
                'shape': (),
                'dtype': np.float64,
                'value': 25.5
            }
        })
        cleanup_fixture(ds, tmp_path)
        
        metadata = {
            'Global_Ancillary_variables': [
                {
                    'name': 'a_double_var',
                    'type': 'double',
                    'applicability': 'Mandatory',
                    'attributes': []
                }
            ]
        }
        
        check_variables(ds, metadata, 'Global_Ancillary_variables',
                      test_results['results'], test_results['section_summaries'])
        
        assert test_results['results'][0][-1] == 'pass'
    
    def test_wrong_data_type_fails_mandatory(self, test_results, cleanup_fixture):
        """Variable with wrong type should FAIL_MANDATORY if Mandatory."""
        ds, tmp_path = NetCDFTestDataFactory.create_test_dataset({
            'a_float_var': {
                'shape': (),
                'dtype': np.int32,
                'value': 25
            }
        })
        cleanup_fixture(ds, tmp_path)
        
        metadata = {
            'Global_Ancillary_variables': [
                {
                    'name': 'a_float_var',
                    'type': 'float',
                    'applicability': 'Mandatory',
                    'attributes': []
                }
            ]
        }
        
        check_variables(ds, metadata, 'Global_Ancillary_variables',
                      test_results['results'], test_results['section_summaries'])
        
        assert test_results['results'][0][-1] == 'fail_mandatory'
    
    def test_wrong_data_type_fails_optional(self, test_results, cleanup_fixture):
        """Variable with wrong type should FAIL_OPTIONAL if Optional."""
        ds, tmp_path = NetCDFTestDataFactory.create_test_dataset({
            'a_float_var': {
                'shape': (),
                'dtype': np.int32,
                'value': 25
            }
        })
        cleanup_fixture(ds, tmp_path)
        
        metadata = {
            'Global_Ancillary_variables': [
                {
                    'name': 'a_float_var',
                    'type': 'float',
                    'applicability': 'Optional',
                    'attributes': []
                }
            ]
        }
        
        check_variables(ds, metadata, 'Global_Ancillary_variables',
                      test_results['results'], test_results['section_summaries'])
        
        assert test_results['results'][0][-1] == 'fail_optional'


# ============================================================================
# Test: Value Range Validation
# ============================================================================

class TestCheckVariablesValueRange:
    """Test value range validation."""
    
    def test_string_value_in_allowed_list_passes(self, test_results, cleanup_fixture):
        """String variable with value in allowed list should pass."""
        ds, tmp_path = NetCDFTestDataFactory.create_test_dataset({
            'var_with_allowed_values': {
                'shape': (),
                'dtype': str,
                'value': "one"
            }
        })
        cleanup_fixture(ds, tmp_path)
        
        metadata = {
            'Global_Ancillary_variables': [
                {
                    'name': 'var_with_allowed_values',
                    'type': 'string',
                    'applicability': 'Mandatory',
                    'attributes': []
                }
            ],
            'allowed_values': {
                'var_with_allowed_values': ["one", "two", "three", "four"]
            }
        }
        
        check_variables(ds, metadata, 'Global_Ancillary_variables',
                      test_results['results'], test_results['section_summaries'])
        
        assert test_results['results'][0][-1] == 'pass'
    
    def test_string_value_not_in_allowed_list_fails_mandatory(self, test_results, cleanup_fixture):
        """String variable with value NOT in allowed list should FAIL_MANDATORY if Mandatory."""
        ds, tmp_path = NetCDFTestDataFactory.create_test_dataset({
            'var_with_allowed_values': {
                'shape': (),
                'dtype': str,
                'value': "five"
            }
        })
        cleanup_fixture(ds, tmp_path)
        
        metadata = {
            'Global_Ancillary_variables': [
                {
                    'name': 'var_with_allowed_values',
                    'type': 'string',
                    'applicability': 'Mandatory',
                    'attributes': []
                }
            ],
            'allowed_values': {
                'var_with_allowed_values': ["one", "two", "three", "four"]
            }
        }
        
        check_variables(ds, metadata, 'Global_Ancillary_variables',
                      test_results['results'], test_results['section_summaries'])
        
        assert test_results['results'][0][-1] == 'fail_mandatory'


# ============================================================================
# Test: Attribute Validation
# ============================================================================

class TestCheckVariablesAttributes:
    """Test attribute validation."""
    
    def test_mandatory_attribute_present_passes(self, test_results, cleanup_fixture):
        """Mandatory attribute that is present should pass."""
        ds, tmp_path = NetCDFTestDataFactory.create_test_dataset({
            'temperature': {
                'shape': (),
                'dtype': np.float32,
                'value': 25.5,
                'attributes': {'units': 'Celsius'}
            }
        })
        cleanup_fixture(ds, tmp_path)
        
        metadata = {
            'Global_Ancillary_variables': [
                {
                    'name': 'temperature',
                    'type': 'float',
                    'applicability': 'Mandatory',
                    'attributes': [
                        {
                            'attribute_name': 'units',
                            'attribute_datatype': 'string',
                            'attribute_value': 'Celsius',
                            'attribute_applicability': 'Mandatory'
                        }
                    ]
                }
            ]
        }
        
        check_variables(ds, metadata, 'Global_Ancillary_variables',
                      test_results['results'], test_results['section_summaries'])
        
        assert test_results['results'][0][-1] == 'pass'
        assert test_results['results'][1][-1] == 'pass'
    
    def test_mandatory_attribute_missing_fails(self, test_results, cleanup_fixture):
        """Mandatory attribute that is missing should fail."""
        ds, tmp_path = NetCDFTestDataFactory.create_test_dataset({
            'temperature': {
                'shape': (),
                'dtype': np.float32,
                'value': 25.5,
                'attributes': {}
            }
        })
        cleanup_fixture(ds, tmp_path)
        
        metadata = {
            'Global_Ancillary_variables': [
                {
                    'name': 'temperature',
                    'type': 'float',
                    'applicability': 'Mandatory',
                    'attributes': [
                        {
                            'attribute_name': 'units',
                            'attribute_datatype': 'string',
                            'attribute_value': 'Celsius',
                            'attribute_applicability': 'Mandatory'
                        }
                    ]
                }
            ]
        }
        
        check_variables(ds, metadata, 'Global_Ancillary_variables',
                      test_results['results'], test_results['section_summaries'])
        
        assert test_results['results'][0][-1] == 'pass'
        assert test_results['results'][1][-1] == 'fail_mandatory'
    
    def test_optional_attribute_missing_marked_not_used(self, test_results, cleanup_fixture):
        """Optional attribute that is missing should be marked NOT_USED."""
        ds, tmp_path = NetCDFTestDataFactory.create_test_dataset({
            'temperature': {
                'shape': (),
                'dtype': np.float32,
                'value': 25.5,
                'attributes': {}
            }
        })
        cleanup_fixture(ds, tmp_path)
        
        metadata = {
            'Global_Ancillary_variables': [
                {
                    'name': 'temperature',
                    'type': 'float',
                    'applicability': 'Optional',
                    'attributes': [
                        {
                            'attribute_name': 'comment',
                            'attribute_datatype': 'string',
                            'attribute_applicability': 'Optional'
                        }
                    ]
                }
            ]
        }
        
        check_variables(ds, metadata, 'Global_Ancillary_variables',
                      test_results['results'], test_results['section_summaries'])
        
        assert test_results['results'][0][-1] == 'pass'
        assert test_results['results'][1][-1] == 'not_used'
    
    def test_attribute_wrong_type_fails(self, test_results, cleanup_fixture):
        """Attribute with wrong type should fail."""
        ds, tmp_path = NetCDFTestDataFactory.create_test_dataset({
            'time_coverage_start': {
                'shape': (),
                'dtype': str,
                'value': '2026-07-07T12:00:00Z',
                'attributes': {'calendar': 123}
            }
        })
        cleanup_fixture(ds, tmp_path)
        
        metadata = {
            'Global_Ancillary_variables': [
                {
                    'name': 'time_coverage_start',
                    'type': 'string',
                    'applicability': 'Mandatory',
                    'attributes': [
                        {
                            'attribute_name': 'calendar',
                            'attribute_datatype': 'string',
                            'attribute_applicability': 'Mandatory'
                        }
                    ]
                }
            ]
        }
        
        check_variables(ds, metadata, 'Global_Ancillary_variables',
                      test_results['results'], test_results['section_summaries'])
        
        assert test_results['results'][0][-1] == 'pass'
        assert test_results['results'][1][-1] == 'fail_mandatory'


# ============================================================================
# Test: Integration
# ============================================================================

class TestCheckVariablesIntegration:
    """Integration tests: multiple variables with complex scenarios."""
    
    def test_mixed_mandatory_and_optional_variables(self, test_results, cleanup_fixture):
        """Test with real Global Ancillary variables from FM301 metadata."""
        ds, tmp_path = NetCDFTestDataFactory.create_test_dataset({
            'volume_number': {
                'shape': (),
                'dtype': np.int32,
                'value': 7
            },
            'time_coverage_start': {
                'shape': (),
                'dtype': str,
                'value': '2026-07-07T12:00:00Z',
                'attributes': {
                    'calendar': 'gregorian',
                    'standard_name': 'time'
                }
            },
            'latitude': {
                'shape': (),
                'dtype': np.float64,
                'value': 48.85,
                'attributes': {
                    'units': 'degrees_north',
                    'standard_name': 'latitude'
                }
            },
            'platform_type': {
                'shape': (),
                'dtype': str,
                'value': 'fixed'
            }
        })
        cleanup_fixture(ds, tmp_path)
        
        metadata = {
            'Global_Ancillary_variables': [
                {
                    'name': 'volume_number',
                    'type': 'int',
                    'applicability': 'Mandatory',
                    'attributes': []
                },
                {
                    'name': 'time_coverage_start',
                    'type': 'string',
                    'applicability': 'Mandatory',
                    'attributes': [
                        {
                            'attribute_name': 'calendar',
                            'attribute_datatype': 'string',
                            'attribute_applicability': 'Mandatory'
                        },
                        {
                            'attribute_name': 'standard_name',
                            'attribute_datatype': 'string',
                            'attribute_applicability': 'Mandatory'
                        }
                    ]
                },
                {
                    'name': 'latitude',
                    'type': 'double',
                    'applicability': 'Mandatory',
                    'attributes': [
                        {
                            'attribute_name': 'units',
                            'attribute_datatype': 'string',
                            'attribute_value': 'degrees_north',
                            'attribute_applicability': 'Mandatory'
                        },
                        {
                            'attribute_name': 'standard_name',
                            'attribute_datatype': 'string',
                            'attribute_value': 'latitude',
                            'attribute_applicability': 'Mandatory'
                        }
                    ]
                },
                {
                    'name': 'platform_type',
                    'type': 'string',
                    'applicability': 'Mandatory',
                    'attributes': []
                },
                {
                    'name': 'status_str',
                    'type': 'string',
                    'applicability': 'Optional',
                    'attributes': []
                }
            ],
            'allowed_values': {
                'platform_type': ['fixed', 'vehicle']
            }
        }
        
        check_variables(ds, metadata, 'Global_Ancillary_variables',
                      test_results['results'], test_results['section_summaries'])
        
        pass_count, fail_mandatory_count, not_used_count = \
            test_results['section_summaries']['Global_Ancillary_variables']
        
        assert pass_count == 8
        assert fail_mandatory_count == 0
        assert not_used_count == 0
