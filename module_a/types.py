from typing import Annotated

FooType = Annotated[str, "This is a FooType"]
BarType = FooType
BazType = BarType
