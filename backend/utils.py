"""Tokenización compartida entre indexer.py y search.py para consistencia BM25."""

STOPWORDS_ES = {
    "a","al","algo","algunas","algunos","ante","antes","como","con",
    "contra","cual","cuando","de","del","desde","donde","durante",
    "e","el","ella","ellas","ellos","en","entre","era","es","esa",
    "esas","ese","eso","esos","esta","estas","este","esto","estos",
    "fue","fueron","ha","han","hasta","hay","la","las","le","les",
    "lo","los","me","mi","mis","muy","más","ni","no","nos","o","otro",
    "para","pero","por","que","quien","se","si","sin","sobre","su",
    "sus","también","tan","te","todo","todos","un","una","unas","unos",
    "y","ya","yo",
}

def tokenize(text: str) -> list[str]:
    """Elimina stopwords y tokens de 1 carácter para mejorar precisión BM25."""
    return [w for w in text.lower().split() if w not in STOPWORDS_ES and len(w) > 1]
