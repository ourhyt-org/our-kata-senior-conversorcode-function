from dataclasses import dataclass
from typing import Any

from src.domain.errors.domain_errors import ValidationError


@dataclass(frozen=True)
class ConversionRequest:
    language_selected: str
    language_target: str
    version: str
    type_architected: str
    options: dict[str, Any]

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "ConversionRequest":
        required = ["languageSelected", "languageTarget", "version", "typeArchitected"]
        for key in required:
            if key not in data or data[key] is None or str(data[key]).strip() == "":
                raise ValidationError(f"request.json missing {key}")
        options = data.get("options")
        if options is None:
            options = {}
        if not isinstance(options, dict):
            raise ValidationError("request.json options must be an object")
        return ConversionRequest(
            language_selected=str(data["languageSelected"]),
            language_target=str(data["languageTarget"]),
            version=str(data["version"]),
            type_architected=str(data["typeArchitected"]),
            options=options,
        )
