import json
import unittest
from types import SimpleNamespace

from app.models.contracts import (
    ErrorCategory,
    ImageInput,
    ModelError,
    ModelRequest,
    ModelResult,
    StructuredOutput,
)
from app.models.gateway import ModelGateway, create_gateway
from app.models.providers.gemini import GeminiProvider


class FakeInteractions:
    def __init__(self, output_text='ok'):
        self.output_text = output_text
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return SimpleNamespace(output_text=self.output_text)


class FakeClient:
    def __init__(self, output_text='ok'):
        self.interactions = FakeInteractions(output_text)


class ModelGatewayTests(unittest.TestCase):
    def test_request_validation(self):
        request = ModelRequest(text='hello', timeout_seconds=5)
        self.assertEqual(request.text, 'hello')

        with self.assertRaises(ValueError):
            ModelRequest()

        with self.assertRaises(ValueError):
            ModelRequest(text='hello', timeout_seconds=0)

    def test_result_validation(self):
        result = ModelResult(
            success=True,
            provider='test',
            model='test-model',
            text='ok',
        )
        self.assertTrue(result.success)

        with self.assertRaises(ValueError):
            ModelResult(success=True, provider='test', model='test', error=ModelError(
                category=ErrorCategory.UNKNOWN_PROVIDER_ERROR,
                retryable=False,
            ))

    def test_missing_api_key(self):
        provider = GeminiProvider(api_key='', model='gemini-3.8-flash')
        result = provider.generate(ModelRequest(text='hello'))
        self.assertFalse(result.success)
        self.assertEqual(result.error.category, ErrorCategory.MISSING_CREDENTIALS)

    def test_provider_selection(self):
        provider = GeminiProvider(api_key='test-key', client=FakeClient())
        gateway = ModelGateway({'gemini': provider}, default_provider='gemini')
        result = gateway.generate(ModelRequest(text='hello'))
        self.assertTrue(result.success)
        self.assertEqual(result.provider, 'gemini')

    def test_unsupported_provider(self):
        gateway = ModelGateway({}, default_provider='ollama')
        result = gateway.generate(ModelRequest(text='hello'))
        self.assertFalse(result.success)
        self.assertEqual(result.error.category, ErrorCategory.UNSUPPORTED_CAPABILITY)

    def test_structured_provider_error(self):
        provider = GeminiProvider(
            api_key='test-key',
            client=FakeClient(output_text='not json'),
        )
        request = ModelRequest(
            text='return JSON',
            structured_output=StructuredOutput(schema={'type': 'object'}),
        )
        result = provider.generate(request)
        self.assertFalse(result.success)
        self.assertEqual(result.error.category, ErrorCategory.INVALID_RESPONSE)

    def test_text_request_construction(self):
        client = FakeClient(output_text='hello')
        provider = GeminiProvider(api_key='test-key', client=client)
        result = provider.generate(ModelRequest(text='hello'))
        self.assertTrue(result.success)
        self.assertEqual(client.interactions.last_kwargs['input'], [
            {'type': 'text', 'text': 'hello'},
        ])

    def test_multimodal_request_construction(self):
        client = FakeClient(output_text=json.dumps({'ok': True}))
        provider = GeminiProvider(api_key='test-key', client=client)
        request = ModelRequest(
            text='describe this',
            images=(ImageInput(data=b'abc', mime_type='image/jpeg'),),
            structured_output=StructuredOutput(schema={'type': 'object'}),
        )
        result = provider.generate(request)
        self.assertTrue(result.success)
        self.assertEqual(client.interactions.last_kwargs['input'][1]['type'], 'image')
        self.assertEqual(client.interactions.last_kwargs['input'][1]['mime_type'], 'image/jpeg')
        self.assertEqual(result.data, {'ok': True})

    def test_gateway_factory_uses_configured_provider(self):
        gateway = create_gateway(
            {'ai': {'provider': 'gemini', 'model': 'gemini-3.8-flash'}},
            environ={},
        )
        self.assertEqual(gateway.provider_names(), ('gemini',))


if __name__ == '__main__':
    unittest.main()
