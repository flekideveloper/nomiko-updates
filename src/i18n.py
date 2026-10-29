"""Offline UI translation catalog.

Always wrap new user-visible text with tr("English source", language).
Only translated catalog entries are localized; missing entries remain readable
English instead of being sent to an external translation API.
"""
from __future__ import annotations

LANGUAGES = {
    'en':'English', 'uk':'Українська', 'ru':'Русский', 'pl':'Polski',
    'de':'Deutsch', 'fr':'Français', 'es':'Español', 'it':'Italiano',
    'pt':'Português', 'pt_BR':'Português (Brasil)', 'nl':'Nederlands',
    'sv':'Svenska', 'no':'Norsk', 'da':'Dansk', 'fi':'Suomi',
    'is':'Íslenska', 'cs':'Čeština', 'sk':'Slovenčina', 'sl':'Slovenščina',
    'hr':'Hrvatski', 'sr':'Српски', 'bs':'Bosanski', 'bg':'Български',
    'ro':'Română', 'hu':'Magyar', 'el':'Ελληνικά', 'tr':'Türkçe',
    'ar':'العربية', 'he':'עברית', 'fa':'فارسی', 'hi':'हिन्दी',
    'bn':'বাংলা', 'ur':'اردو', 'pa':'ਪੰਜਾਬੀ', 'gu':'ગુજરાતી',
    'ta':'தமிழ்', 'te':'తెలుగు', 'ml':'മലയാളം', 'kn':'ಕನ್ನಡ',
    'mr':'मराठी', 'ne':'नेपाली', 'si':'සිංහල', 'th':'ไทย',
    'vi':'Tiếng Việt', 'id':'Bahasa Indonesia', 'ms':'Bahasa Melayu',
    'tl':'Filipino', 'ko':'한국어', 'ja':'日本語', 'zh_CN':'简体中文',
    'zh_TW':'繁體中文', 'et':'Eesti', 'lv':'Latviešu', 'lt':'Lietuvių',
    'sq':'Shqip', 'mk':'Македонски', 'ka':'ქართული', 'hy':'Հայերեն',
    'az':'Azərbaycanca', 'kk':'Қазақша', 'uz':'Oʻzbek', 'mn':'Монгол',
    'sw':'Kiswahili', 'af':'Afrikaans', 'ca':'Català', 'eu':'Euskara',
    'gl':'Galego', 'cy':'Cymraeg', 'ga':'Gaeilge', 'mt':'Malti',
}

# Offline, reviewed primary UI translations. English fallback for unknown words.
TRANSLATIONS = {
'uk': {
 'Restore previous tabs on startup':'Відновлювати попередні вкладки під час запуску',
 'Restores normal tabs after restarting NOMIKO. Private windows are never restored.':'Відновлює звичайні вкладки після перезапуску NOMIKO. Приватні вікна ніколи не відновлюються.',
 'Widgets':'Віджети','Widget spacing':'Відступи віджетів','Widget columns':'Колонки віджетів',
 'Graphite grey · Default':'Графітово-сіра · За замовчуванням',
 'Midnight black':'Нічна чорна','Comfortable':'Зручна','Compact':'Компактна',
 'Settings':'Налаштування','General':'Загальні','Appearance':'Вигляд',
 'Privacy':'Приватність','Downloads':'Завантаження','Language':'Мова',
 'Support':'Підтримка','Save':'Зберегти','Cancel':'Скасувати',
 'Default accent':'Акцент за замовчуванням','Change accent color':'Змінити акцентний колір',
 'Theme':'Тема','Dark':'Темна','Light':'Світла',
 'Search':'Пошук','Default search engine':'Пошуковик за замовчуванням',
 'Available search engines':'Доступні пошуковики','Download folder':'Папка завантажень',
 'Choose folder':'Обрати папку','Tab position':'Розташування вкладок',
 'Top':'Зверху','Bottom':'Знизу','Left':'Зліва','Right':'Справа',
 'Tab label':'Відображення вкладок','Icon only':'Лише іконка',
 'Title only':'Лише назва','Icon and title':'Іконка та назва',
 'New tab':'Нова вкладка','Close tab':'Закрити вкладку',
 'Back':'Назад','Forward':'Вперед','Reload':'Оновити',
 'Home':'Головна','Bookmark':'Закладка','Private window':'Приватне вікно',
 'Menu':'Меню','Minimize':'Згорнути','Maximize':'Розгорнути',
 'Close':'Закрити','Find on page':'Знайти на сторінці',
 'Bookmarks':'Закладки','History':'Історія','New private window':'Нове приватне вікно',
 'Clear browsing data':'Очистити дані перегляду','About NOMIKO':'Про NOMIKO',
 'Support development':'Підтримати розробку','Ready':'Готово',
 'Appearance and tabs':'Оформлення та вкладки',
 'Search and homepage':'Пошук і головна сторінка',
 'Search or enter a website':'Пошук або адреса сайту',
 'No account required.':'Реєстрація не потрібна.',
 'YOUR INTERNET, YOUR RULES':'ТВІЙ ІНТЕРНЕТ, ТВОЇ ПРАВИЛА',
 'PRIVATE SESSION':'ПРИВАТНИЙ СЕАНС',
 'Choose at least one search engine.':'Оберіть принаймні один пошуковик.',
 'Show downloads':'Показати завантаження','Settings saved':'Налаштування збережено',
},
'ru': {
 'Restore previous tabs on startup':'Восстанавливать вкладки при запуске',
 'Restores normal tabs after restarting NOMIKO. Private windows are never restored.':'Обычные вкладки восстанавливаются после перезапуска NOMIKO. Приватные окна не восстанавливаются.',
 'Settings':'Настройки','General':'Общие','Appearance':'Внешний вид',
 'Privacy':'Приватность','Downloads':'Загрузки','Language':'Язык',
 'Support':'Поддержка','Save':'Сохранить','Cancel':'Отмена',
 'Default accent':'Стандартный акцент','Change accent color':'Изменить цвет акцента',
 'Theme':'Тема','Dark':'Тёмная','Light':'Светлая',
 'Search':'Поиск','Default search engine':'Поисковик по умолчанию',
 'Available search engines':'Доступные поисковики','Download folder':'Папка загрузок',
 'Choose folder':'Выбрать папку','Tab position':'Расположение вкладок',
 'Top':'Сверху','Bottom':'Снизу','Left':'Слева','Right':'Справа',
 'Tab label':'Отображение вкладок','Icon only':'Только значок',
 'Title only':'Только название','Icon and title':'Значок и название',
 'New tab':'Новая вкладка','Close tab':'Закрыть вкладку',
 'Back':'Назад','Forward':'Вперёд','Reload':'Обновить',
 'Home':'Главная','Bookmark':'Закладка','Private window':'Приватное окно',
 'Menu':'Меню','Minimize':'Свернуть','Maximize':'Развернуть',
 'Close':'Закрыть','Bookmarks':'Закладки','History':'История',
 'Support development':'Поддержать разработку','Ready':'Готово',
},
'pl': {
 'Settings':'Ustawienia','General':'Ogólne','Appearance':'Wygląd','Privacy':'Prywatność',
 'Downloads':'Pobrane','Language':'Język','Support':'Wsparcie','Save':'Zapisz',
 'Cancel':'Anuluj','Default accent':'Domyślny akcent','Theme':'Motyw',
 'Dark':'Ciemny','Light':'Jasny','Search':'Wyszukiwanie',
 'Default search engine':'Domyślna wyszukiwarka','Available search engines':'Dostępne wyszukiwarki',
 'Download folder':'Folder pobierania','Choose folder':'Wybierz folder',
 'Tab position':'Położenie kart','Top':'Góra','Bottom':'Dół','Left':'Lewo','Right':'Prawo',
 'Icon only':'Tylko ikona','Title only':'Tylko tytuł','Icon and title':'Ikona i tytuł',
 'New tab':'Nowa karta','Close tab':'Zamknij kartę',
 'Back':'Wstecz','Forward':'Dalej','Reload':'Odśwież','Home':'Strona główna',
 'Bookmark':'Zakładka','Menu':'Menu','Minimize':'Minimalizuj','Maximize':'Maksymalizuj',
 'Close':'Zamknij','Bookmarks':'Zakładki','History':'Historia',
 'Support development':'Wesprzyj rozwój','Ready':'Gotowe',
},
'de': {
 'Settings':'Einstellungen','General':'Allgemein','Appearance':'Darstellung',
 'Privacy':'Datenschutz','Downloads':'Downloads','Language':'Sprache',
 'Support':'Unterstützen','Save':'Speichern','Cancel':'Abbrechen',
 'Default accent':'Standardakzent','Theme':'Design','Dark':'Dunkel','Light':'Hell',
 'Search':'Suche','Default search engine':'Standardsuchmaschine',
 'Available search engines':'Verfügbare Suchmaschinen','Download folder':'Downloadordner',
 'Choose folder':'Ordner auswählen','Tab position':'Tab-Position',
 'Top':'Oben','Bottom':'Unten','Left':'Links','Right':'Rechts',
 'Icon only':'Nur Symbol','Title only':'Nur Titel','Icon and title':'Symbol und Titel',
 'New tab':'Neuer Tab','Close tab':'Tab schließen','Back':'Zurück','Forward':'Vorwärts',
 'Reload':'Neu laden','Home':'Startseite','Bookmark':'Lesezeichen','Menu':'Menü',
 'Minimize':'Minimieren','Maximize':'Maximieren','Close':'Schließen',
 'Bookmarks':'Lesezeichen','History':'Verlauf','Ready':'Bereit',
},
'fr': {
 'Settings':'Paramètres','General':'Général','Appearance':'Apparence',
 'Privacy':'Confidentialité','Downloads':'Téléchargements','Language':'Langue',
 'Support':'Soutien','Save':'Enregistrer','Cancel':'Annuler',
 'Default accent':'Couleur par défaut','Theme':'Thème','Dark':'Sombre','Light':'Clair',
 'Search':'Recherche','Default search engine':'Moteur de recherche par défaut',
 'Available search engines':'Moteurs de recherche disponibles','Download folder':'Dossier de téléchargement',
 'Choose folder':'Choisir un dossier','Tab position':'Position des onglets',
 'Top':'Haut','Bottom':'Bas','Left':'Gauche','Right':'Droite',
 'Icon only':'Icône seule','Title only':'Titre seul','Icon and title':'Icône et titre',
 'New tab':'Nouvel onglet','Close tab':'Fermer l’onglet',
 'Back':'Retour','Forward':'Avancer','Reload':'Actualiser',
 'Home':'Accueil','Bookmark':'Favori','Menu':'Menu','Minimize':'Réduire',
 'Maximize':'Agrandir','Close':'Fermer','Bookmarks':'Favoris','History':'Historique',
},
'es': {
 'Settings':'Configuración','General':'General','Appearance':'Apariencia',
 'Privacy':'Privacidad','Downloads':'Descargas','Language':'Idioma',
 'Support':'Apoyo','Save':'Guardar','Cancel':'Cancelar','Theme':'Tema',
 'Dark':'Oscuro','Light':'Claro','Search':'Búsqueda',
 'Default accent':'Acento predeterminado','Default search engine':'Buscador predeterminado',
 'Available search engines':'Buscadores disponibles','Download folder':'Carpeta de descargas',
 'Choose folder':'Elegir carpeta','Tab position':'Posición de pestañas',
 'Top':'Arriba','Bottom':'Abajo','Left':'Izquierda','Right':'Derecha',
 'Icon only':'Solo icono','Title only':'Solo título','Icon and title':'Icono y título',
 'New tab':'Nueva pestaña','Close tab':'Cerrar pestaña','Back':'Atrás',
 'Forward':'Adelante','Reload':'Recargar','Home':'Inicio',
 'Bookmark':'Marcador','Menu':'Menú','Minimize':'Minimizar',
 'Maximize':'Maximizar','Close':'Cerrar','Bookmarks':'Marcadores','History':'Historial',
},
}

def tr(source: str, language: str = 'en') -> str:
    """Translate offline. Source English is the stable key for future UI strings."""
    return TRANSLATIONS.get(language, {}).get(source, source)


def coverage(language: str, keys: set[str]) -> tuple[int, int]:
    """Use in translation QA to locate missing translations before releases."""
    return len(keys & TRANSLATIONS.get(language, {}).keys()), len(keys)


# Shared home/search strings. Missing translations fall back to English.
HOME_TRANSLATIONS = {
 'uk': {
   'Explore freely. Customize everything.':'Досліджуй вільно. Налаштовуй усе під себе.',
   'Temporary data. Private mode does not hide your IP address.':'Тимчасові дані. Приватний режим не приховує твою IP-адресу.',
   'Search with':'Шукати через', 'Search engine':'Пошуковик',
   'Search or enter a website…':'Пошук або адреса сайту…',
   'Nothing in your bookmarks or history matches yet.':'У закладках та історії поки немає збігів.',
   'Search on':'Шукати через', 'Local results':'Локальні результати',
   'Search the wider web':'Пошук у всьому інтернеті',
   'Your local index · No Wikipedia requests':'Твій локальний індекс · Без запитів до Wikipedia',
   'NOMIKO Search currently searches your saved bookmarks and visited-page titles and addresses locally. It is not yet a search engine that indexes the entire public web. External search happens only when you choose a provider.':
   'NOMIKO Search наразі шукає лише у твоїх закладках, історії та адресах сайтів. Він ще не індексує весь інтернет. Зовнішній пошук запускається лише після твого вибору.',
 },
 'ru': {
   'Explore freely. Customize everything.':'Исследуй свободно. Настраивай всё под себя.',
   'Temporary data. Private mode does not hide your IP address.':'Временные данные. Приватный режим не скрывает IP-адрес.',
   'Search with':'Искать через', 'Search engine':'Поисковик',
   'Search or enter a website…':'Поиск или адрес сайта…',
   'Nothing in your bookmarks or history matches yet.':'В закладках и истории пока нет совпадений.',
   'Search on':'Искать через', 'Local results':'Локальные результаты',
   'Search the wider web':'Поиск в интернете',
   'Your local index · No Wikipedia requests':'Локальный индекс · Без запросов к Wikipedia',
 },
}
for _code, _strings in HOME_TRANSLATIONS.items():
    TRANSLATIONS.setdefault(_code, {}).update(_strings)
