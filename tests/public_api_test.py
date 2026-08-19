import unittest

import pydraw


class PublicApiTest(unittest.TestCase):

    def test_root_wildcard_exports_only_the_supported_public_api(self):
        namespace = {}
        exec('from pydraw import *', namespace)

        exported = {name for name in namespace if name != '__builtins__'}
        self.assertEqual(exported, set(pydraw.__all__))

    def test_root_does_not_export_implementation_details(self):
        self.assertFalse(hasattr(pydraw, 'PIXEL_RATIO'))
        self.assertNotIn('PIXEL_RATIO', pydraw.__all__)
        self.assertNotIn('NoneType', pydraw.__all__)
        self.assertNotIn('math', pydraw.__all__)
        self.assertNotIn('PackageNotFoundError', pydraw.__all__)
        self.assertNotIn('RenderBatch', pydraw.__all__)
        self.assertNotIn('ScreenBackend', pydraw.__all__)

    def test_extension_layers_define_their_own_public_apis(self):
        from pydraw import render, runtime

        self.assertIn('RenderBatch', render.__all__)
        self.assertIn('RenderQueue', render.__all__)
        self.assertIn('ScreenBackend', runtime.__all__)
        self.assertIn('install_runtime', runtime.__all__)


if __name__ == '__main__':
    unittest.main()
