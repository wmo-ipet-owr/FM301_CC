import numpy as np

from fm301_cc import extract_scalar_value_from_variable


class FakeVariable:
    """Minimal test double for netCDF4.Variable.

    We only emulate the attributes and indexing modes used by
    extract_scalar_value_from_variable:
    - shape/ndim/dtype for branch selection.
    - var[...] and var[:] for value extraction.
    """

    def __init__(self, value, shape, ndim, dtype):
        # Keep raw payload in _value and expose metadata separately,
        # similar to how netCDF variables expose array shape/type.
        self._value = value
        self.shape = shape
        self.ndim = ndim
        self.dtype = dtype

    def __getitem__(self, item):
        """Support the indexing forms used by the production function.

        - Ellipsis (`var[...]`) returns the scalar payload.
        - Full slice (`var[:]`) returns the full payload.
        - Any other key is delegated to the wrapped value.
        """
        if item is Ellipsis:
            return self._value
        if isinstance(item, slice) and item == slice(None):
            return self._value
        return self._value[item]


def test_extracts_scalar_numeric_as_python_native_type_and_sets_scalar_flag():
    var = FakeVariable(value=np.int32(7), shape=(), ndim=0, dtype=np.dtype("i4"))

    value, is_scalar = extract_scalar_value_from_variable(var)

    assert value == 7
    assert isinstance(value, int)
    assert is_scalar is True


def test_extracts_scalar_nc_string_as_python_str_and_sets_scalar_flag():
    var = FakeVariable(value="2026-01-01T00:00:00Z", shape=(), ndim=0, dtype=np.dtype("O"))

    value, is_scalar = extract_scalar_value_from_variable(var)

    assert value == "2026-01-01T00:00:00Z"
    assert isinstance(value, str)
    assert is_scalar is True


def test_extracts_1d_char_array_as_string_and_sets_scalar_flag_true():
    var = FakeVariable(
        value=np.array([b"A", b"B", b"C"], dtype="S1"),
        shape=(3,),
        ndim=1,
        dtype=np.dtype("S1"),
    )

    value, is_scalar = extract_scalar_value_from_variable(var)

    assert value == "ABC"
    assert isinstance(value, str)
    assert is_scalar is True


def test_non_scalar_values_return_compact_array_string_and_sets_scalar_flag_false():
    var = FakeVariable(
        value=np.array([[1.2345, 2.3456], [3.4567, 4.5678]], dtype=float),
        shape=(2, 2),
        ndim=2,
        dtype=np.dtype("f8"),
    )

    value, is_scalar = extract_scalar_value_from_variable(var)

    assert isinstance(value, str)
    assert value == "[[1.23, 2.35],\n [3.46, 4.57]]"
    assert is_scalar is False
