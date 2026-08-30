Original path: tests/types/test_list.py
Snapshot commit: 43b2e383b229219cb15606f17991562f5ada553f
Original lines: 240-305

        ta.validate_python([1, 'x', 'y'])
    # insert_assert(exc_info.value.errors(include_url=False))
    assert exc_info.value.errors(include_url=False) == [
        {
            'type': 'int_parsing',
            'loc': (1,),
            'msg': 'Input should be a valid integer, unable to parse string as an integer',
            'input': 'x',
        },
        {
            'type': 'int_parsing',
            'loc': (2,),
            'msg': 'Input should be a valid integer, unable to parse string as an integer',
            'input': 'y',
        },
    ]

    with pytest.raises(ValidationError) as exc_info:
        ta.validate_python(1)
    # insert_assert(exc_info.value.errors(include_url=False))
    assert exc_info.value.errors(include_url=False) == [
        {'type': 'list_type', 'loc': (), 'msg': 'Input should be a valid list', 'input': 1}
    ]


def test_list_wrong_type_default():
    """It should not validate default value by default"""

    class Model(BaseModel):
        v: list[int] = 'a'

    m = Model()
    assert m.v == 'a'


def test_list_strict() -> None:
    ta = TypeAdapter(list[int])

    assert ta.validate_python((1, 2)) == [1, 2]
    assert ta.validate_python(('1', 2)) == [1, 2]
    # Tuple should be rejected
    with pytest.raises(ValidationError) as exc_info:
        ta.validate_python((1, 2), strict=True)
    assert exc_info.value.errors(include_url=False) == [
        {'type': 'list_type', 'loc': (), 'msg': 'Input should be a valid list', 'input': (1, 2)}
    ]
    # Strict in each list item
    with pytest.raises(ValidationError) as exc_info:
        ta.validate_python(['1', 2], strict=True)
    assert exc_info.value.errors(include_url=False) == [
        {'type': 'int_type', 'loc': (0,), 'msg': 'Input should be a valid integer', 'input': '1'}
    ]


def test_bare_mutable_sequence() -> None:
    """A bare `MutableSequence` should behave as a bare `list`, as `MutableSequence[int]` does."""
    ta = TypeAdapter(MutableSequence)

    assert ta.validate_python([1, '2']) == [1, '2']
    assert ta.validate_python((1, '2')) == [1, '2']

    with pytest.raises(ValidationError) as exc_info:
        ta.validate_python('abc')
    assert exc_info.value.errors(include_url=False) == [
        {'type': 'list_type', 'loc': (), 'msg': 'Input should be a valid list', 'input': 'abc'}
    ]
