Experiment to use static analysis to detected `Annotated` aliases in Python code.

Example:
``` python
# module_a/types.py
from typing import Annotated
FooType = Annotated
BarType = FooType

# module_a/__init__.py
from .types import FooType, BarType
from typing import Annotated as BazType

# main.py
from module_a import FooType, BarType, BazType
```

Analyzer should detect that `FooType`, `BarType`, `BazType` are aliases of `Annotated`.


