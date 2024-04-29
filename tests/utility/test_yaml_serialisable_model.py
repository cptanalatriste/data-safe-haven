from pytest import fixture, raises

from data_safe_haven.exceptions import (
    DataSafeHavenConfigError,
    DataSafeHavenParameterError,
)
from data_safe_haven.utility.yaml_serialisable_model import YAMLSerialisableModel


class ExampleYAMLSerialisableModel(YAMLSerialisableModel):
    config_type = "Example"
    string: str
    integer: int
    list_of_integers: list[int]


@fixture
def example_config_class():
    return ExampleYAMLSerialisableModel(
        string="hello", integer=5, list_of_integers=[1, 2, 3]
    )


@fixture
def example_config_yaml():
    return "\n".join(["string: 'abc'", "integer: -3", "list_of_integers: [-1,0,1]"])


class TestYAMLSerialisableModel:
    def test_constructor(self, example_config_class):
        assert isinstance(example_config_class, ExampleYAMLSerialisableModel)
        assert isinstance(example_config_class, YAMLSerialisableModel)
        assert example_config_class.string == "hello"

    def test_to_yaml(self, example_config_class):
        yaml = example_config_class.to_yaml()
        assert isinstance(yaml, str)
        assert "string: hello" in yaml
        assert "integer: 5" in yaml
        assert "config_type" not in yaml

    def test_from_yaml(self, example_config_yaml):
        example_config_class = ExampleYAMLSerialisableModel.from_yaml(
            example_config_yaml
        )
        assert isinstance(example_config_class, ExampleYAMLSerialisableModel)
        assert isinstance(example_config_class, YAMLSerialisableModel)
        assert example_config_class.string == "abc"
        assert example_config_class.integer == -3
        assert example_config_class.list_of_integers == [-1, 0, 1]

    def test_from_yaml_invalid_yaml(self):
        yaml = "\n".join(["string: 'abc'", "integer: -3", "list_of_integers: [-1,0,1"])
        with raises(
            DataSafeHavenConfigError,
            match="Could not parse Example configuration as YAML.",
        ):
            ExampleYAMLSerialisableModel.from_yaml(yaml)

    def test_from_yaml_not_dict(self):
        yaml = """42"""
        with raises(
            DataSafeHavenConfigError,
            match="Unable to parse Example configuration as a dict.",
        ):
            ExampleYAMLSerialisableModel.from_yaml(yaml)

    def test_from_yaml_validation_error(self):
        yaml = "\n".join(
            ["string: 'abc'", "integer: 'not an integer'", "list_of_integers: [-1,0,1]"]
        )

        with raises(
            DataSafeHavenParameterError,
            match="Could not load Example configuration.",
        ):
            ExampleYAMLSerialisableModel.from_yaml(yaml)
