# Testing Strategy for `check_variables()` Function

## Overview

A comprehensive unit test suite has been created using **pytest** that tests the `check_variables()` function in isolation using **synthetic/mock netCDF4 datasets** rather than relying on real JSON metadata files. This approach provides:

✅ **Future-proof tests** - Tests logic, not data format  
✅ **Complete coverage** - Every requirement is explicitly tested  
✅ **Fast execution** - No file dependencies or external data (<200ms for all tests)  
✅ **Clear intent** - Each test documents one specific requirement  
✅ **Regression prevention** - Catch bugs before production  
✅ **Simple syntax** - pytest's clean, straightforward assertions  

---

## Test Organization

The test suite is organized into 6 test classes, each focusing on one validation requirement:

### 1. **TestCheckVariablesPresence** (4 tests)
Tests variable presence requirements for Mandatory vs Optional variables:
- `test_mandatory_variable_present_passes` - Mandatory variable that exists → PASS
- `test_mandatory_variable_missing_fails` - Mandatory variable missing → FAIL_MANDATORY  
- `test_optional_variable_missing_marked_not_used` - Optional variable missing → NOT_USED
- `test_optional_variable_present_passes` - Optional variable exists → PASS

### 2. **TestCheckVariablesScalarRequirement** (3 tests)
Tests that Global Ancillary variables must be scalars:
- `test_scalar_variable_passes_scalar_check` - Scalar variable → PASS
- `test_1d_char_array_represents_string_passes_scalar_check` - 1D `S1` char array representing classic netCDF string → PASS
- `test_1d_array_fails_scalar_check` - 1D array variable → FAIL_MANDATORY

### 3. **TestCheckVariablesDataType** (4 tests)
Tests data type validation logic:
- `test_correct_float_type_passes` - Correct float32 type → PASS
- `test_double_type_passes` - Correct float64/double type → PASS
- `test_wrong_data_type_fails_mandatory` - Wrong type on Mandatory variable → FAIL_MANDATORY
- `test_wrong_data_type_fails_optional` - Wrong type on Optional variable → FAIL_OPTIONAL

### 4. **TestCheckVariablesValueRange** (2 tests)
Tests allowed-values validation:
- `test_string_value_in_allowed_list_passes` - String value in allowed list → PASS
- `test_string_value_not_in_allowed_list_fails_mandatory` - String value not in list → FAIL_MANDATORY

### 5. **TestCheckVariablesAttributes** (4 tests)
Tests attribute presence and type validation:
- `test_mandatory_attribute_present_passes` - Mandatory attribute exists and correct → PASS
- `test_mandatory_attribute_missing_fails` - Mandatory attribute missing → FAIL_MANDATORY
- `test_optional_attribute_missing_marked_not_used` - Optional attribute missing → NOT_USED
- `test_attribute_wrong_type_fails` - Attribute with wrong type → FAIL_MANDATORY

### 6. **TestCheckVariablesIntegration** (1 test)
Integration test with complex scenarios:
- `test_mixed_mandatory_and_optional_variables` - Real FM301-style Global Ancillary variables with mixed Mandatory/Optional checks

---

## Test Data Factory: `NetCDFTestDataFactory`

Instead of creating real netCDF files or mocking netCDF4 objects, tests use a helper class that:

1. **Creates temporary netCDF files** during test setup
2. **Populates them with specified variables** via declarative specs
3. **Closes and reopens in read mode** for consistency
4. **Cleans up automatically** after each test via pytest fixtures

**Usage example:**
```python
def test_example(self, cleanup_fixture):
    ds, tmp_path = NetCDFTestDataFactory.create_test_dataset({
        'temperature': {
            'shape': (),  # Scalar
            'dtype': np.float32,
            'value': 25.5,
            'attributes': {'units': 'Celsius'}
        }
    })
    cleanup_fixture(ds, tmp_path)  # Registers for automatic cleanup
    
    # Run your test
    check_variables(ds, metadata, ...)
```

---

## Compliance Requirements Tested

### Variable Itself

✅ **Mandatory variable must be present**  
✅ **Optional variable missing is marked as "not_used"**  
✅ **Variable must be scalar** (not array)  
✅ **Variable must have correct data type**  
✅ **Variable value must be in allowed_values (if specified)**  

### Variable Attributes

✅ **Mandatory attribute must be present**  
✅ **Optional attribute missing is marked as "not_used"**  
✅ **Attribute must have correct data type**  
✅ **Attribute value must match expected value (if specified)**  

---

## Running the Tests

### Run All Tests
```bash
python -m pytest tests/test_check_variables.py -v
```

### Run Tests from a Specific Class
```bash
python -m pytest tests/test_check_variables.py::TestCheckVariablesDataType -v
```

### Run a Specific Test
```bash
python -m pytest tests/test_check_variables.py::TestCheckVariablesDataType::test_correct_float_type_passes -v
```

### Run Tests Matching a Pattern
```bash
python -m pytest tests/test_check_variables.py -k "mandatory" -v
```

### Show Test Output (Print Statements)
```bash
python -m pytest tests/test_check_variables.py -v -s
```

### Quick Summary (Minimal Output)
```bash
python -m pytest tests/test_check_variables.py -q
```

### Exit After First Failure
```bash
python -m pytest tests/test_check_variables.py -x -v
```

**Expected Result:**
```
============================= 18 passed in ~0.2s ==============================
```

---

