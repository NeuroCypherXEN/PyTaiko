import unittest
from unittest.mock import Mock, patch

from libs.texture import (
    FramedTexture,
    SkinInfo,
    Texture,
    TextureWrapper,
)


class TestSkinInfo(unittest.TestCase):
    """Test cases for the SkinInfo dataclass."""

    def test_initialization(self):
        """Test SkinInfo initialization."""
        skin_info = SkinInfo(
            x=100.0,
            y=200.0,
            font_size=24,
            width=300.0,
            height=100.0,
            text={"en": "Test", "ja": "テスト"}
        )

        self.assertEqual(skin_info.x, 100.0)
        self.assertEqual(skin_info.y, 200.0)
        self.assertEqual(skin_info.font_size, 24)
        self.assertEqual(skin_info.width, 300.0)
        self.assertEqual(skin_info.height, 100.0)
        self.assertEqual(skin_info.text, {"en": "Test", "ja": "テスト"})

    def test_repr(self):
        """Test SkinInfo string representation."""
        skin_info = SkinInfo(
            x=100.0,
            y=200.0,
            font_size=24,
            width=300.0,
            height=100.0,
            text={"en": "Test"}
        )

        repr_str = repr(skin_info)
        self.assertIn("100.0", repr_str)
        self.assertIn("200.0", repr_str)


class TestTexture(unittest.TestCase):
    """Test cases for the Texture class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_texture = Mock()
        self.mock_texture.width = 100
        self.mock_texture.height = 50

    @patch('libs.texture.ray')
    def test_initialization_single_texture(self, mock_ray):
        """Test Texture initialization with single texture."""
        texture = Texture(
            name="test_texture",
            texture=self.mock_texture,
            init_vals={}
        )

        self.assertEqual(texture.name, "test_texture")
        self.assertEqual(texture.texture, self.mock_texture)
        self.assertEqual(texture.width, 100)
        self.assertEqual(texture.height, 50)
        self.assertEqual(texture.x, [0])
        self.assertEqual(texture.y, [0])

    @patch('libs.texture.ray')
    def test_initialization_with_init_vals(self, mock_ray):
        """Test Texture initialization with init_vals."""
        init_vals = {"x": 10, "y": 20}
        texture = Texture(
            name="test",
            texture=self.mock_texture,
            init_vals=init_vals
        )

        self.assertEqual(texture.init_vals, init_vals)
        self.assertEqual(texture.name, "test")

    @patch('libs.texture.ray')
    def test_default_values(self, mock_ray):
        """Test Texture default values."""
        texture = Texture(name="test", texture=self.mock_texture, init_vals={})

        self.assertEqual(texture.x, [0])
        self.assertEqual(texture.y, [0])
        self.assertEqual(texture.x2, [100])
        self.assertEqual(texture.y2, [50])
        self.assertEqual(texture.controllable, [False])

    @patch('libs.texture.ray')
    def test_repr(self, mock_ray):
        """Test Texture string representation."""
        texture = Texture(name="test", texture=self.mock_texture, init_vals={})

        repr_str = repr(texture)
        self.assertIn("test", repr_str)


class TestFramedTexture(unittest.TestCase):
    """Test cases for the FramedTexture class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_textures = [Mock() for _ in range(4)]
        for tex in self.mock_textures:
            tex.width = 200
            tex.height = 100

    @patch('libs.texture.ray')
    def test_initialization(self, mock_ray):
        """Test FramedTexture initialization."""
        framed = FramedTexture(
            name="test_framed",
            texture=self.mock_textures,
            init_vals={}
        )

        self.assertEqual(framed.name, "test_framed")
        self.assertEqual(framed.texture, self.mock_textures)
        self.assertEqual(framed.width, 200)
        self.assertEqual(framed.height, 100)
        self.assertEqual(framed.x, [0])
        self.assertEqual(framed.y, [0])

    @patch('libs.texture.ray')
    def test_default_values(self, mock_ray):
        """Test FramedTexture default values."""
        framed = FramedTexture(
            name="test",
            texture=self.mock_textures,
            init_vals={}
        )

        self.assertEqual(framed.x, [0])
        self.assertEqual(framed.y, [0])
        self.assertEqual(framed.x2, [200])
        self.assertEqual(framed.y2, [100])


class TestTextureWrapper(unittest.TestCase):
    """Test cases for the TextureWrapper class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_texture = Mock()
        self.mock_texture.width = 100
        self.mock_texture.height = 50

    @patch('libs.texture.get_config')
    @patch('libs.texture.Path')
    def test_initialization(self, mock_path_cls, mock_get_config):
        """Test TextureWrapper initialization."""
        mock_get_config.return_value = {'paths': {'skin': 'TestSkin'}}

        # Mock the skin_config.json file
        mock_path_instance = Mock()
        mock_config_path = Mock()
        mock_config_path.exists.return_value = True
        mock_config_path.read_text.return_value = '{"screen": {"width": 1280, "height": 720}}'
        mock_path_instance.__truediv__ = Mock(return_value=mock_config_path)
        mock_path_cls.return_value = mock_path_instance

        wrapper = TextureWrapper()

        self.assertEqual(wrapper.screen_width, 1280)
        self.assertEqual(wrapper.screen_height, 720)
        self.assertIsInstance(wrapper.textures, dict)

    @patch('libs.texture.get_config')
    @patch('libs.texture.Path')
    def test_get_animation(self, mock_path_cls, mock_get_config):
        """Test getting animation from list."""
        mock_get_config.return_value = {'paths': {'skin': 'TestSkin'}}

        # Mock the skin_config.json file
        mock_path_instance = Mock()
        mock_config_path = Mock()
        mock_config_path.exists.return_value = True
        mock_config_path.read_text.return_value = '{"screen": {"width": 1280, "height": 720}}'
        mock_path_instance.__truediv__ = Mock(return_value=mock_config_path)
        mock_path_cls.return_value = mock_path_instance

        mock_animation = Mock()

        wrapper = TextureWrapper()
        wrapper.animations = {0: mock_animation}

        result = wrapper.get_animation(0)

        self.assertEqual(result, mock_animation)

    @patch('libs.texture.get_config')
    @patch('libs.texture.Path')
    @patch('libs.texture.ray')
    def test_read_tex_obj_data(self, mock_ray, mock_path_cls, mock_get_config):
        """Test reading texture object data from JSON."""
        mock_get_config.return_value = {'paths': {'skin': 'TestSkin'}}

        # Mock the skin_config.json file
        mock_path_instance = Mock()
        mock_config_path = Mock()
        mock_config_path.exists.return_value = True
        mock_config_path.read_text.return_value = '{"screen": {"width": 1280, "height": 720}}'

        mock_path_instance.__truediv__ = Mock(return_value=mock_config_path)
        mock_path_cls.return_value = mock_path_instance

        wrapper = TextureWrapper()

        # Create a mock texture object
        mock_texture = Mock()
        mock_texture.x = [0]
        mock_texture.y = [0]

        # Test with a dictionary mapping
        tex_mapping = {"x": 10, "y": 20}
        wrapper._read_tex_obj_data(tex_mapping, mock_texture)

        # Verify the texture attributes were updated (they are lists)
        self.assertEqual(mock_texture.x, [10])
        self.assertEqual(mock_texture.y, [20])

    @patch('libs.texture.get_config')
    @patch('libs.texture.Path')
    def test_read_tex_obj_data_not_exists(self, mock_path_cls, mock_get_config):
        """Test reading texture data with empty mapping."""
        mock_get_config.return_value = {'paths': {'skin': 'TestSkin'}}

        # Mock the skin_config.json file
        mock_path_instance = Mock()
        mock_config_path = Mock()
        mock_config_path.exists.return_value = True
        mock_config_path.read_text.return_value = '{"screen": {"width": 1280, "height": 720}}'

        mock_path_instance.__truediv__ = Mock(return_value=mock_config_path)
        mock_path_cls.return_value = mock_path_instance

        wrapper = TextureWrapper()

        # Create a mock texture object
        mock_texture = Mock()
        mock_texture.x = [0]
        mock_texture.y = [0]

        # Test with empty mapping (should not modify texture)
        tex_mapping = {}
        wrapper._read_tex_obj_data(tex_mapping, mock_texture)

        # Verify the texture attributes remained unchanged
        self.assertEqual(mock_texture.x, [0])
        self.assertEqual(mock_texture.y, [0])

if __name__ == '__main__':
    unittest.main()
