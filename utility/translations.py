import os
from typing import Callable, Dict

import hikari
import lightbulb
from fluent.runtime import FluentLocalization, FluentResourceLoader
from fluent.runtime.errors import FluentFormatError

BASE_LOCALE_PATH = 'locales'
_translation_cache: Dict[str, FluentLocalization] = {}
_loader = FluentResourceLoader(f'{BASE_LOCALE_PATH}/{{locale}}')


for locale in os.listdir(BASE_LOCALE_PATH):

    path = os.path.join(BASE_LOCALE_PATH, locale)
    if not os.path.isdir(path):
        continue

    # This prints out what will be loaded
    ftl_files = [f.replace('.ftl', '.ftl') for f in os.listdir(path) if f.endswith('.ftl')]

    if not ftl_files:
        print(f'⚠️ No .ftl files found for locale: {locale}')
        continue

    try:
        fl = FluentLocalization(locales=[locale, 'en-US'], resource_ids=ftl_files, resource_loader=_loader)
        _translation_cache[locale] = fl
    except FluentFormatError as e:
        print(f'❌ FluentFormatError in locale {locale}: {e}')
    except Exception as e:
        print(f'❌ General error in locale {locale}: {e}')


def fluent_provider() -> Callable[[str], Dict[hikari.Locale, str]]:
    def provider(key: str) -> Dict[hikari.Locale, str]:
        result = {}
        fallback_locale = 'en-US'

        for loc_str, fl in _translation_cache.items():
            try:
                value = fl.format_value(key)
                if key == value:
                    fallback_fl = _translation_cache.get(fallback_locale)
                    value = fallback_fl.format_value(key)
                result[loc_str] = value
            except Exception:
                continue
        return result

    return provider


def translation(ctx: lightbulb.Context | lightbulb.components.MenuContext) -> Callable:
    def _(key: str, **kwargs) -> str:
        localized = _translation_cache[str(ctx.interaction.locale)].format_value(key, kwargs or None)
        if localized != key:
            return localized
        fl = _translation_cache['en-US']
        return fl.format_value(key, kwargs or None)

    return _
