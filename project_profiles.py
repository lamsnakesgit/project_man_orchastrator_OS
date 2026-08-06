"""
Конфигурация профилей проектов для ИИ-оркестратора.
Определяет системные инструкции, модели по умолчанию и наборы инструментов (capabilities/toolsets)
для различных категорий задач (web, mobile_dev, marketing, general).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any


@dataclass
class ProjectProfile:
    """
    Класс профиля проекта.
    Содержит системные инструкции, выбранную модель по умолчанию и доступные инструменты.
    """
    name: str
    description: str
    system_instructions: str
    default_model: str
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразует объект профиля в словарь.
        """
        return {
            "name": self.name,
            "description": self.description,
            "system_instructions": self.system_instructions,
            "default_model": self.default_model,
            "capabilities": self.capabilities,
            "metadata": self.metadata,
        }


# Реестр доступных профилей проектов
PROJECT_PROFILES: Dict[str, ProjectProfile] = {
    "web": ProjectProfile(
        name="web",
        description="Профиль для веб-разработки (React, TypeScript, HTML/CSS, Node.js/FastAPI)",
        system_instructions=(
            "Вы — специалист по веб-разработке. Вы отлично разбираетесь в создании веб-приложений, "
            "frontend (React, Vue, Tailwind CSS, TypeScript) и backend (FastAPI, Express, Node.js). "
            "Пишите чистый, адаптивный, безопасный и поддерживаемый код с автотестами."
        ),
        default_model="claude-3.5-opus",
        capabilities=["code_editor", "browser_automation", "terminal", "git_worktree"],
        metadata={"category": "development", "stack": ["react", "typescript", "fastapi"]}
    ),
    "mobile_dev": ProjectProfile(
        name="mobile_dev",
        description="Профиль для мобильной разработки (iOS, Android, React Native, Flutter, Swift, Kotlin)",
        system_instructions=(
            "Вы — специалист по мобильной разработке. Вы специализируетесь на разработке нативных "
            "и кроссплатформенных мобильных приложений (Swift, Kotlin, React Native, Flutter). "
            "Уделяйте внимание мобильному UI/UX, производительности, работе с офлайн-кэшем и мобильным API."
        ),
        default_model="gemini-3.1-pro",
        capabilities=["code_editor", "mobile_emulator", "terminal", "git_worktree"],
        metadata={"category": "development", "stack": ["swift", "kotlin", "react-native", "flutter"]}
    ),
    "marketing": ProjectProfile(
        name="marketing",
        description="Профиль для цифрового маркетинга, копирайтинга и SEO-анализа",
        system_instructions=(
            "Вы — специалист по цифровому маркетингу и контент-стратегии. Вы создаете "
            "продающие тексты, SEO-оптимизированные статьи, рекламные карусели и анализируете "
            "маркетинговые метрики и целевую аудиторию."
        ),
        default_model="gemini-3.5",
        capabilities=["web_search", "content_generator", "analytics", "seo_auditor"],
        metadata={"category": "marketing", "tools": ["seo", "copywriting", "analytics"]}
    ),
    "general": ProjectProfile(
        name="general",
        description="Универсальный профиль ИИ-оркестратора для общих задач",
        system_instructions=(
            "Вы — автономный ИИ-оркестратор общего профиля. Ваша задача — принимать задачи, "
            "анализировать требования, писать код, выполнять отладку и формировать Pull Request'ы."
        ),
        default_model="antigravity-pro",
        capabilities=["code_editor", "terminal", "git_worktree", "web_search"],
        metadata={"category": "general", "default": True}
    ),
}


def get_project_profile(profile_name: str = "general") -> ProjectProfile:
    """
    Возвращает конфигурацию профиля по названию.
    Если указанный профиль не найден, возвращает профиль по умолчанию ('general').
    """
    if not profile_name or profile_name not in PROJECT_PROFILES:
        return PROJECT_PROFILES["general"]
    return PROJECT_PROFILES[profile_name]


def list_project_profiles() -> List[str]:
    """
    Возвращает список всех доступных имен профилей.
    """
    return list(PROJECT_PROFILES.keys())


def get_default_model(profile_name: str = "general") -> str:
    """
    Возвращает модель по умолчанию для указанного профиля.
    """
    profile = get_project_profile(profile_name)
    return profile.default_model
