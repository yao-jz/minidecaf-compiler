# Temporary variables.
class Temp:
    def __init__(self, index: int) -> None:
        self.index = index

    def __str__(self) -> str:
        return "_T" + str(self.index)
