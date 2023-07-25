from typing import Any, Dict
import yaml
from collections import UserDict


class ConfigAccessor(UserDict):
    def __init__(self, file_name: str) -> None:
        super().__init__()
        self.file_name = file_name

        try:
            with open(file_name, "r") as config_file:
                self.data = yaml.safe_load(config_file)
        except FileNotFoundError:
            print(f"File {self.file_name} does not exist")
        except:
            raise

    def update(self, other) -> None:
        self.data.update(other.data if "data" in other else other)

    def __getattr__(self, item) -> Any:
        if item in self.data:
            return self.data[item]

        raise AttributeError(f"'{item} not defined in {self.file_name}")

    def __str__(self) -> str:
        return str(self.data)

    def __repr__(self) -> str:
        return repr(self.data)
