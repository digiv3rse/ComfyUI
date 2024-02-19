# coding: utf-8

"""
    Generated by: https://github.com/openapi-json-schema-tools/openapi-json-schema-generator
"""

from comfy.api.shared_imports.response_imports import *  # pyright: ignore [reportWildcardImportFromLibrary]

from .content.text_plain import schema as text_plain_schema


@dataclasses.dataclass(frozen=True)
class ApiResponse(api_response.ApiResponse):
    body: str
    headers: schemas.Unset


class ResponseFor200(api_client.OpenApiResponse[ApiResponse]):
    @classmethod
    def get_response(cls, response, headers, body) -> ApiResponse:
        return ApiResponse(response=response, body=body, headers=headers)


    class TextPlainMediaType(api_client.MediaType):
        schema: typing_extensions.TypeAlias = text_plain_schema.Schema
    content = {
        'text/plain': TextPlainMediaType,
    }