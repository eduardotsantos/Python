"""Flask extensions initialization."""
from flask_babel import Babel

babel = Babel()

# Supported languages
LANGUAGES = {
    'pt_BR': 'Português (Brasil)',
    'en': 'English',
    'es': 'Español'
}

DEFAULT_LANGUAGE = 'pt_BR'

# Language codes mapping (URL-safe to Babel format)
LANGUAGE_CODES = {
    'pt-BR': 'pt_BR',
    'pt_BR': 'pt_BR',
    'en': 'en',
    'es': 'es'
}
