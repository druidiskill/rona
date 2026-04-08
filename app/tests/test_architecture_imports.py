import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKIP_DIRS = {'.venv', '__pycache__', '.git', 'tests', '.tmp_base_structure'}
LEGACY_PATTERNS = (
    'from database',
    'import database',
    'from google_calendar',
    'import google_calendar',
)
APP_SHIM_PATTERNS = (
    re.compile(r'^from\s+db\b'),
    re.compile(r'^import\s+db\b'),
    re.compile(r'^from\s+calendar_integration\b'),
    re.compile(r'^import\s+calendar_integration\b'),
    re.compile(r'^from\s+telegram_bot\b'),
    re.compile(r'^import\s+telegram_bot\b'),
    re.compile(r'^from\s+vk_bot\b'),
    re.compile(r'^import\s+vk_bot\b'),
    re.compile(r'^from\s+core\b'),
    re.compile(r'^import\s+core\b'),
)


class TestArchitectureImports(unittest.TestCase):
    def test_no_legacy_imports_outside_compat_layers(self):
        violations = []

        for path in ROOT.rglob('*.py'):
            rel = path.relative_to(ROOT)
            if any(part in SKIP_DIRS for part in rel.parts):
                continue

            text = path.read_text(encoding='utf-8')
            for lineno, line in enumerate(text.splitlines(), start=1):
                if any(pattern in line for pattern in LEGACY_PATTERNS):
                    violations.append(f"{rel}:{lineno}: {line.strip()}")

        self.assertEqual([], violations, 'Found legacy imports:\n' + '\n'.join(violations))

    def test_app_package_uses_only_app_level_imports(self):
        violations = []
        app_root = ROOT / 'app'

        for path in app_root.rglob('*.py'):
            rel = path.relative_to(ROOT)
            if any(part in SKIP_DIRS for part in rel.parts):
                continue

            text = path.read_text(encoding='utf-8')
            for lineno, line in enumerate(text.splitlines(), start=1):
                stripped = line.strip()
                if any(pattern.search(stripped) for pattern in APP_SHIM_PATTERNS):
                    violations.append(f"{rel}:{lineno}: {stripped}")

        self.assertEqual([], violations, 'Found shim imports inside app package:\n' + '\n'.join(violations))


if __name__ == '__main__':
    unittest.main()
