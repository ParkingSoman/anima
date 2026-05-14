"""Per-Anima JSON-on-disk persistence (E5).

Single-writer JSON store with master-plan §5.1 (behavioral record) and §5.2
(interpreted state) regions kept on disk as separate files. See
:mod:`anima.persistence.store` for the layout and atomic-write semantics.
"""

from anima.persistence.store import AnimaStore, AnimaStoreSnapshot

__all__ = ["AnimaStore", "AnimaStoreSnapshot"]
