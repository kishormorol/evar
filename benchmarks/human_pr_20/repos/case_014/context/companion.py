Original path: tests/test_json_schema.py
Snapshot commit: 22b6bcecdd2be748ff2567e4e83a853be84554e2
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

    @pydantic.dataclasses.dataclass(config=ConfigDict(validate_by_alias=False, validate_by_name=True))
    class Dataclass:
        my_field: str = Field(alias='myAlias')

    adapter = TypeAdapter(Dataclass)
    assert list(adapter.json_schema()['properties']) == ['my_field']


def test_validate_by_alias_false_is_scoped_to_its_own_model():
    class Inner(BaseModel):
        model_config = ConfigDict(validate_by_alias=False, validate_by_name=True)
        inner_field: str = Field(alias='innerAlias')
