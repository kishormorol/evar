Original path: tests/test_json_schema.py
Snapshot commit: f2cb3992433c6c81179c2dd688fccfe4fa486cdd
Original lines: 116-164

except ImportError:
    email_validator = None

from .utils import dataclass_decorators

T = TypeVar('T')


def test_by_alias():
    class ApplePie(BaseModel):
        model_config = ConfigDict(title='Apple Pie')
        a: float = Field(alias='Snap')
        b: int = Field(10, alias='Crackle')

    assert ApplePie.model_json_schema() == {
        'type': 'object',
        'title': 'Apple Pie',
        'properties': {
            'Snap': {'type': 'number', 'title': 'Snap'},
            'Crackle': {'type': 'integer', 'title': 'Crackle', 'default': 10},
        },
        'required': ['Snap'],
    }
    assert list(ApplePie.model_json_schema(by_alias=True)['properties'].keys()) == ['Snap', 'Crackle']
    assert list(ApplePie.model_json_schema(by_alias=False)['properties'].keys()) == ['a', 'b']


def test_validate_by_alias_false_uses_the_field_name():
    class Model(BaseModel):
        model_config = ConfigDict(validate_by_alias=False, validate_by_name=True)
        my_field: str = Field(alias='myAlias')

    assert list(Model.model_json_schema()['properties']) == ['my_field']
    # Serialization is governed by `serialize_by_alias`, which this leaves alone:
    assert list(Model.model_json_schema(mode='serialization')['properties']) == ['myAlias']

    # Which is the right description only because the alias is the one key refused:
    assert Model(my_field='x').my_field == 'x'
    with pytest.raises(ValidationError):
        Model.model_validate({'myAlias': 'x'})

    # The alias is resolved in the shared generator, so a dataclass carrying the same config
    # is described the same way:
    @pydantic.dataclasses.dataclass(config=ConfigDict(validate_by_alias=False, validate_by_name=True))
    class Dataclass:
        my_field: str = Field(alias='myAlias')

    adapter = TypeAdapter(Dataclass)
    assert list(adapter.json_schema()['properties']) == ['my_field']
