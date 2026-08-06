import os
import sys
import unittest
import yaml

# Добавляем корневую директорию проекта в sys.path для импорта модулей
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from project_profiles import (
    ProjectProfile,
    PROJECT_PROFILES,
    get_project_profile,
    list_project_profiles,
    get_default_model,
)


class TestProjectProfiles(unittest.TestCase):
    """
    Модульные тесты для модуля конфигурации профилей проектов (project_profiles.py)
    и маршрутизации моделей LiteLLM.
    """

    def test_load_all_profiles(self):
        """
        Проверка корректной загрузки всех предустановленных профилей.
        """
        expected_profiles = ["web", "mobile_dev", "marketing", "general"]
        for profile_name in expected_profiles:
            profile = get_project_profile(profile_name)
            self.assertIsInstance(profile, ProjectProfile)
            self.assertEqual(profile.name, profile_name)
            self.assertTrue(len(profile.system_instructions) > 0, f"Системные инструкции для {profile_name} не должны быть пустыми")
            self.assertTrue(len(profile.default_model) > 0, f"Модель по умолчанию для {profile_name} не должна быть пустой")
            self.assertTrue(isinstance(profile.capabilities, list), f"Capabilities для {profile_name} должен быть списком")
            self.assertTrue(len(profile.capabilities) > 0, f"Набор инструментов для {profile_name} должен быть непустым")

    def test_unknown_profile_fallback(self):
        """
        Проверка возврата профиля по умолчанию ('general') при запросе неизвестного или пустого профиля.
        """
        fallback_1 = get_project_profile("unknown_profile_xyz")
        self.assertEqual(fallback_1.name, "general")

        fallback_2 = get_project_profile("")
        self.assertEqual(fallback_2.name, "general")

        fallback_3 = get_project_profile(None)
        self.assertEqual(fallback_3.name, "general")

    def test_list_project_profiles(self):
        """
        Проверка получения списка именованных профилей.
        """
        profiles = list_project_profiles()
        self.assertIn("web", profiles)
        self.assertIn("mobile_dev", profiles)
        self.assertIn("marketing", profiles)
        self.assertIn("general", profiles)
        self.assertEqual(len(profiles), 4)

    def test_get_default_model(self):
        """
        Проверка маппинга моделей по умолчанию для профилей.
        """
        self.assertEqual(get_default_model("web"), "claude-3.5-opus")
        self.assertEqual(get_default_model("mobile_dev"), "gemini-3.1-pro")
        self.assertEqual(get_default_model("marketing"), "gemini-3.5")
        self.assertEqual(get_default_model("general"), "antigravity-pro")
        self.assertEqual(get_default_model("non_existent"), "antigravity-pro")

    def test_model_routing_maps_to_litellm_config(self):
        """
        Проверка соответствия моделей по умолчанию из профилей алиасам в litellm_config.yaml.
        """
        config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "litellm_config.yaml"))
        self.assertTrue(os.path.exists(config_path), "Файл litellm_config.yaml должен существовать")

        with open(config_path, "r", encoding="utf-8") as f:
            litellm_config = yaml.safe_load(f)

        configured_models = {
            m["model_name"] for m in litellm_config.get("model_list", []) if "model_name" in m
        }

        # Все модели по умолчанию для профилей должны присутствовать в litellm_config.yaml
        for profile_name in list_project_profiles():
            default_model = get_default_model(profile_name)
            self.assertIn(
                default_model,
                configured_models,
                f"Модель '{default_model}' из профиля '{profile_name}' не найдена в litellm_config.yaml"
            )

    def test_profile_to_dict(self):
        """
        Проверка сериализации профиля в словарь.
        """
        profile = get_project_profile("web")
        data = profile.to_dict()
        self.assertEqual(data["name"], "web")
        self.assertEqual(data["default_model"], "claude-3.5-opus")
        self.assertIn("capabilities", data)
        self.assertIn("system_instructions", data)


if __name__ == "__main__":
    unittest.main()
